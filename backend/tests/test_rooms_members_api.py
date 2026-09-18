"""r002 接口层用例：取 Token / 移出成员 / 任命协管 / 移交房主 / 结束房间（外部调用打桩）。

设计事实源：`docs/02-modules/r002-livekit.md` §5（接口清单）、§6.4、§8（并发与边界）、§9（验证矩阵）。
约定：LiveKit 调用一律打桩（`app.services.livekit.*`），不联网；库侧断言走真实 PostgreSQL（conftest 的回滚事务）。
"""
from __future__ import annotations

import base64
import json

import pytest

from app.services import livekit as livekit_service
from helpers import register_user, session_cookie

TOPIC = {"topic": "custom", "topicLabel": "测试主题", "title": "测试房间", "description": ""}


def login(client, user) -> None:
    name, value = session_cookie(user.id)
    client.cookies.set(name, value)


def create_room(client, title: str = "测试房间") -> dict:
    resp = client.post("/api/rooms", json={**TOPIC, "title": title})
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def join_as_member(client, host, room_id: str, applicant) -> str:
    """申请人提交 → 切回 Host 批准，返回成员 user_id（结束时会话停在 Host）。"""
    login(client, applicant)
    created = client.post(f"/api/rooms/{room_id}/join-requests", json={"message": "想加入"})
    assert created.status_code == 201, created.text
    request_id = created.json()["data"]["id"]
    login(client, host)
    approved = client.post(f"/api/join-requests/{request_id}/approve")
    assert approved.status_code == 200, approved.text
    return applicant.id


def claims_of(token: str) -> dict:
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))


# ---------------- 取 Token ----------------

def test_token_requires_login(client, db):
    assert client.post("/api/rooms/room_x/token").status_code == 401


def test_token_denied_for_non_member_and_ended_room(client, db):
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    outsider = register_user(db, "路人")
    login(client, outsider)
    denied = client.post(f"/api/rooms/{room['id']}/token")
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "NOT_MEMBER"

    login(client, host)
    assert client.post(f"/api/rooms/{room['id']}/end").status_code == 200
    ended = client.post(f"/api/rooms/{room['id']}/token")
    assert ended.status_code == 409
    assert ended.json()["error"]["code"] == "ROOM_ENDED"


def test_token_grants_follow_role(client, db):
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    guest = register_user(db, "参与者")
    login(client, guest)
    rid = client.post(f"/api/rooms/{room['id']}/join-requests", json={"message": "想加入"}).json()["data"]["id"]
    login(client, host)
    assert client.post(f"/api/join-requests/{rid}/approve").status_code == 200

    host_data = client.post(f"/api/rooms/{room['id']}/token").json()["data"]
    host_claims = claims_of(host_data["token"])
    assert host_claims["sub"] == host.id
    assert host_claims["video"]["roomAdmin"] is True
    assert host_claims["video"]["room"] == room["id"]

    login(client, guest)
    guest_data = client.post(f"/api/rooms/{room['id']}/token").json()["data"]
    guest_claims = claims_of(guest_data["token"])
    assert guest_claims["sub"] == guest.id
    assert guest_claims["video"].get("roomAdmin", False) is False
    assert guest_data["roomName"] == room["id"]
    assert guest_data["url"].startswith("wss://")
    assert guest_data["expiresIn"] > 0


# ---------------- 移出成员 ----------------

def test_kick_member_by_host_marks_kicked_and_applies_livekit(client, db, monkeypatch):
    calls = []
    monkeypatch.setattr(livekit_service, "remove_participant", lambda room, uid, settings=None: calls.append((room, uid)) or True)
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    guest = register_user(db, "参与者")
    join_as_member(client, host, room["id"], guest)
    login(client, host)
    resp = client.delete(f"/api/rooms/{room['id']}/members/{guest.id}")
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["livekitApplied"] is True
    assert data["member"]["status"] == "inactive" and data["member"]["exitReason"] == "kicked"
    assert calls == [(room["id"], guest.id)]


def test_kick_survives_livekit_failure(client, db, monkeypatch):
    def boom(room, uid, settings=None):
        raise RuntimeError("cloud down")

    monkeypatch.setattr(livekit_service, "remove_participant", boom)
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    guest = register_user(db, "参与者")
    join_as_member(client, host, room["id"], guest)
    login(client, host)
    resp = client.delete(f"/api/rooms/{room['id']}/members/{guest.id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["livekitApplied"] is False  # 外部失败不回滚库状态
    assert resp.json()["data"]["member"]["status"] == "inactive"


def test_kick_guard_matrix(client, db, monkeypatch):
    monkeypatch.setattr(livekit_service, "remove_participant", lambda room, uid, settings=None: True)
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    mod = register_user(db, "协管")
    other = register_user(db, "另一个")
    join_as_member(client, host, room["id"], mod)
    join_as_member(client, host, room["id"], other)

    # 任命 mod 为协管
    login(client, host)
    assert client.patch(f"/api/rooms/{room['id']}/members/{mod.id}/role", json={"role": "moderator"}).status_code == 200
    # 踢自己 → 400
    assert client.delete(f"/api/rooms/{room['id']}/members/{host.id}").status_code == 400
    # 协管踢房主 → 403
    login(client, mod)
    assert client.delete(f"/api/rooms/{room['id']}/members/{host.id}").status_code == 403
    # 协管踢协管：再任命一个协管然后互踢
    login(client, host)
    assert client.patch(f"/api/rooms/{room['id']}/members/{other.id}/role", json={"role": "moderator"}).status_code == 200
    login(client, mod)
    peer = client.delete(f"/api/rooms/{room['id']}/members/{other.id}")
    assert peer.status_code == 403 and peer.json()["error"]["code"] == "FORBIDDEN"
    # 协管踢普通参与者：先把 other 降回成员
    login(client, host)
    assert client.patch(f"/api/rooms/{room['id']}/members/{other.id}/role", json={"role": "participant"}).status_code == 200
    login(client, mod)
    assert client.delete(f"/api/rooms/{room['id']}/members/{other.id}").status_code == 200
    # 非管理者（普通参与者）踢人 → 403
    third = register_user(db, "普通")
    join_as_member(client, host, room["id"], third)
    login(client, third)
    assert client.delete(f"/api/rooms/{room['id']}/members/{mod.id}").status_code == 403


# ---------------- 角色与移交 ----------------

def test_role_change_guards(client, db):
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    member = register_user(db, "成员")
    join_as_member(client, host, room["id"], member)
    login(client, host)
    # 允许值只有 moderator / participant：host 由「移交房主」负责（非法值走统一信封 400 VALIDATION）
    bad = client.patch(f"/api/rooms/{room['id']}/members/{member.id}/role", json={"role": "host"})
    assert bad.status_code == 400 and bad.json()["error"]["code"] == "VALIDATION"
    assert client.patch(f"/api/rooms/{room['id']}/members/{host.id}/role", json={"role": "moderator"}).status_code == 400
    ok = client.patch(f"/api/rooms/{room['id']}/members/{member.id}/role", json={"role": "moderator"})
    assert ok.status_code == 200 and ok.json()["data"]["member"]["role"] == "moderator"
    login(client, member)
    assert client.patch(f"/api/rooms/{room['id']}/members/{host.id}/role", json={"role": "moderator"}).status_code == 403


def test_transfer_host(client, db):
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    member = register_user(db, "接手人")
    join_as_member(client, host, room["id"], member)
    login(client, host)
    assert client.post(f"/api/rooms/{room['id']}/transfer-host", json={"userId": host.id}).status_code == 400
    resp = client.post(f"/api/rooms/{room['id']}/transfer-host", json={"userId": member.id})
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["room"]["hostId"] == member.id
    assert data["previousHost"]["role"] == "moderator"
    assert data["newHost"]["role"] == "host"
    # 移交后原房主（现为协管）不能再移交
    third = register_user(db, "第三方")
    join_as_member(client, member, room["id"], third)
    login(client, host)
    assert client.post(f"/api/rooms/{room['id']}/transfer-host", json={"userId": third.id}).status_code == 403


def test_end_room_reports_livekit_applied(client, db, monkeypatch):
    calls = []
    monkeypatch.setattr(livekit_service, "delete_room", lambda room, settings=None: calls.append(room) or True)
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    resp = client.post(f"/api/rooms/{room['id']}/end")
    assert resp.status_code == 200
    assert resp.json()["data"]["livekitApplied"] is True
    assert calls == [room["id"]]

# ---------------- 等候与入场（ADR-0012 修订口径，cp-r002-4 转正）----------------
#
# 目标口径（用户 2026-09-18）：容量按**在场**算（不占座、无「未入场」概念）；
#   申请不校验容量 → 申请人总能进等待室；批准不校验容量 → 获批后**自动进入**；
#   真正的容量闸在**取票**（`POST /token`）：在场 >= capacity → 409 ROOM_FULL，「失败回主界面」。
# 当前实现仍是 r001 的「在册口径 + 申请/批准时拦截」，故本用例先标 xfail；cp-r002-4 落地后去掉标记。


@pytest.mark.xfail(reason="ADR-0012 修订口径待 cp-r002-4 落地（容量改在场口径、取票时才拦）", strict=False)
def test_capacity_is_enforced_at_token_time_with_presence(client, db, monkeypatch):
    """满员＝在场满：申请可提交、批准不拦、取票时第 N+1 人被拒。"""
    from app.services import rooms as rooms_service

    monkeypatch.setattr(livekit_service, "list_participant_identities", lambda room, settings=None: ["usr_a", "usr_b"])
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    db.execute("UPDATE rooms SET capacity = 2 WHERE id = %s", (room["id"],))

    waiter = register_user(db, "排队的")
    login(client, waiter)
    created = client.post(f"/api/rooms/{room['id']}/join-requests", json={"message": "排队中"})
    assert created.status_code == 201, created.text  # 申请不校验容量
    request_id = created.json()["data"]["id"]

    login(client, host)
    assert client.post(f"/api/join-requests/{request_id}/approve").status_code == 200  # 批准不校验容量

    login(client, waiter)
    token = client.post(f"/api/rooms/{room['id']}/token")  # 在场已满 → 取票被拒
    assert token.status_code == 409 and token.json()["error"]["code"] == "ROOM_FULL"

    # 有人离场（在场数降到 1）→ 取票通过
    monkeypatch.setattr(livekit_service, "list_participant_identities", lambda room, settings=None: ["usr_a"])
    assert client.post(f"/api/rooms/{room['id']}/token").status_code == 200
    assert rooms_service is not None
