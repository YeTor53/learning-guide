"""r012 用例：超管隐身进房与旁路治理（block A）。

口径来源：docs/rounds/r012-superadmin-console/design.md §2、ADR-0024（D1~D4）。
约定：LiveKit 调用一律打桩（不联网、零配额）；库侧断言走真实 PostgreSQL（conftest 的回滚事务）。
"""
from __future__ import annotations

import base64
import json

import pytest

from app.repositories import rooms as rooms_repo
from app.repositories import users as users_repo
from app.services import livekit as livekit_service
from app.services.roles import SUPERADMIN
from helpers import register_user, session_cookie

TOPIC = {"topic": "custom", "topicLabel": "超管", "title": "超管用例房", "description": ""}
CAPACITY = 8


def login(client, user) -> None:
    name, value = session_cookie(user.id)
    client.cookies.set(name, value)


def create_room(client, title: str = "超管用例房") -> dict:
    resp = client.post("/api/rooms", json={**TOPIC, "title": title})
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def promote(db, user):
    """把用户提为超管（角色在每次请求时从库里读，故直接改库即可）。"""
    assert users_repo.set_user_role(db, user.id, SUPERADMIN) == 1
    return user


def join_as_member(client, host, room_id: str, applicant) -> str:
    login(client, applicant)
    created = client.post(f"/api/rooms/{room_id}/join-requests", json={"message": "想加入"})
    assert created.status_code == 201, created.text
    login(client, host)
    approved = client.post(f"/api/join-requests/{created.json()['data']['id']}/approve")
    assert approved.status_code == 200, approved.text
    return applicant.id


def fill_room(db, room_id: str, count: int) -> None:
    """直接写库把房间填到容量（超管用例只关心「满员」这个事实）。"""
    for index in range(count):
        member = register_user(db, f"填充{index}")
        rooms_repo.insert_member(
            db,
            rooms_repo.NewMember(
                id=f"mem_superadmin_{room_id}_{index}",
                room_id=room_id,
                user_id=member.id,
                role="participant",
            ),
        )


def claims_of(token: str) -> dict:
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))


# ---------------- 取票：隐身 + 只读 + 不占人数 ----------------

def test_superadmin_token_is_hidden_readonly_and_records_visit(client, db) -> None:
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    admin = register_user(db, "超管同学")
    promote(db, admin)

    login(client, admin)
    resp = client.post(f"/api/rooms/{room['id']}/token")
    assert resp.status_code == 200, resp.text

    claims = claims_of(resp.json()["data"]["token"])
    assert claims["sub"] == admin.id
    assert claims["video"]["hidden"] is True                 # 对其它参与者不可见（ADR-0024 D2）
    assert claims["video"]["canPublish"] is False            # 只管理：不发布音视频（D3）
    assert claims["video"]["canPublishData"] is False
    assert claims["video"].get("roomAdmin", False) is False  # 不借 LiveKit 管控权（D4）
    assert claims["attributes"] == {"lg-role": "superadmin"} # 给转写 worker 的判据
    assert claims["roomConfig"]["maxParticipants"] == CAPACITY

    # 旁路记账：进的是 room_visits，不是 room_members
    visits = rooms_repo.list_open_visits(db, room["id"])
    assert [v.user_id for v in visits] == [admin.id]

    detail = client.get(f"/api/rooms/{room['id']}").json()["data"]
    assert detail["room"]["myRole"] == "superadmin"
    assert detail["room"]["memberCount"] == 1
    assert admin.id not in {member["userId"] for member in detail["members"]}
    assert all(member["role"] != "host" or member["userId"] == host.id for member in detail["members"])


def test_superadmin_enters_full_room_while_stranger_cannot(client, db) -> None:
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    fill_room(db, room["id"], CAPACITY - 1)                  # 房主 + 7 = 满员
    assert client.get(f"/api/rooms/{room['id']}").json()["data"]["room"]["memberCount"] == CAPACITY

    stranger = register_user(db, "路人")
    login(client, stranger)
    denied = client.post(f"/api/rooms/{room['id']}/token")
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "NOT_MEMBER"

    admin = register_user(db, "超管")
    promote(db, admin)
    login(client, admin)
    assert client.post(f"/api/rooms/{room['id']}/token").status_code == 200
    # 超管不占人数：满员房里进出自如，在册数不变
    assert client.get(f"/api/rooms/{room['id']}").json()["data"]["room"]["memberCount"] == CAPACITY


def test_superadmin_cannot_enter_ended_room_or_unknown_room(client, db) -> None:
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    admin = register_user(db, "超管")
    promote(db, admin)
    login(client, admin)
    assert client.post("/api/rooms/room_not_exists/token").status_code == 404

    login(client, host)
    assert client.post(f"/api/rooms/{room['id']}/end").status_code == 200
    login(client, admin)
    ended = client.post(f"/api/rooms/{room['id']}/token")
    assert ended.status_code == 409
    assert ended.json()["error"]["code"] == "ROOM_ENDED"


# ---------------- 旁路治理：与房主同结果 ----------------

def test_superadmin_kicks_and_ends_other_peoples_room(client, db, monkeypatch) -> None:
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        livekit_service, "remove_participant", lambda room, uid, settings=None: calls.append((room, uid)) or True
    )
    monkeypatch.setattr(livekit_service, "delete_room", lambda room, settings=None: True)

    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    guest = register_user(db, "参与者")
    guest_id = join_as_member(client, host, room["id"], guest)

    admin = register_user(db, "超管")
    promote(db, admin)
    login(client, admin)

    kicked = client.delete(f"/api/rooms/{room['id']}/members/{guest_id}")
    assert kicked.status_code == 200, kicked.text
    assert kicked.json()["data"]["member"]["status"] == "inactive"
    assert rooms_repo.get_active_member(db, room["id"], guest_id) is None
    assert calls == [(room["id"], guest_id)]

    ended = client.post(f"/api/rooms/{room['id']}/end")
    assert ended.status_code == 200, ended.text
    assert rooms_repo.get_room(db, room["id"]).room.status == "ended"

    bodies = [m.message.body for m in rooms_repo.list_recent_messages(db, room["id"], 20)]
    assert any("被移出房间" in body for body in bodies)
    assert "房间已结束" in bodies


def test_plain_participant_still_cannot_govern(client, db) -> None:
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    guest = register_user(db, "参与者")
    login(client, guest)
    created = client.post(f"/api/rooms/{room['id']}/join-requests", json={"message": "想加入"})
    login(client, host)
    client.post(f"/api/join-requests/{created.json()['data']['id']}/approve")

    login(client, guest)
    assert client.delete(f"/api/rooms/{room['id']}/members/{host.id}").status_code == 403
    assert client.post(f"/api/rooms/{room['id']}/end").status_code == 403
    assert client.get(f"/api/rooms/{room['id']}/join-requests?status=pending").status_code == 403


def test_superadmin_sees_pending_requests_of_foreign_room(client, db) -> None:
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    applicant = register_user(db, "申请人")
    login(client, applicant)
    assert client.post(f"/api/rooms/{room['id']}/join-requests", json={"message": "想加入"}).status_code == 201

    admin = register_user(db, "超管")
    promote(db, admin)
    login(client, admin)
    assert client.get(f"/api/rooms/{room['id']}").json()["data"]["room"]["pendingCount"] == 1
    listed = client.get(f"/api/rooms/{room['id']}/join-requests?status=pending")
    assert listed.status_code == 200, listed.text
    assert len(listed.json()["data"]["requests"]) == 1


def test_superadmin_leave_closes_visit_without_touching_members(client, db) -> None:
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    admin = register_user(db, "超管")
    promote(db, admin)
    login(client, admin)
    assert client.post(f"/api/rooms/{room['id']}/token").status_code == 200
    assert len(rooms_repo.list_open_visits(db, room["id"])) == 1

    assert client.post(f"/api/rooms/{room['id']}/leave").status_code == 200
    assert rooms_repo.list_open_visits(db, room["id"]) == []
    assert client.get(f"/api/rooms/{room['id']}").json()["data"]["room"]["memberCount"] == 1


def test_room_list_shows_superadmin_role(client, db) -> None:
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client, "列表里的房")
    admin = register_user(db, "超管")
    promote(db, admin)
    login(client, admin)
    listing = client.get("/api/rooms?status=all&limit=100").json()["data"]["rooms"]
    assert next(item for item in listing if item["id"] == room["id"])["myRole"] == "superadmin"
