"""r004 接口层用例：群聊消息 / 举手 / 焦点（真实 PG，回滚事务；不联网）。

设计事实源：`docs/rounds/r004-room-extras/design.md` §4（接口）、§10（验证矩阵 E1~E6）
约定：与 r002 用例同款——`client` 夹具把 `db_conn` 覆盖成测试事务里的连接，用例结束整批回滚。
"""
from __future__ import annotations

import pytest

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
    """申请人提交 → 切回 Host 批准（结束时会话停在 Host）。"""
    login(client, applicant)
    created = client.post(f"/api/rooms/{room_id}/join-requests", json={"message": "想加入"})
    assert created.status_code == 201, created.text
    request_id = created.json()["data"]["id"]
    login(client, host)
    approved = client.post(f"/api/join-requests/{request_id}/approve")
    assert approved.status_code == 200, approved.text
    return applicant.id


def setup_room(client, db):
    """房主 + 一个已批准成员；返回 (host, member, room)。"""
    host = register_user(db, "房主")
    member = register_user(db, "成员")
    login(client, host)
    room = create_room(client)
    join_as_member(client, host, room["id"], member)
    return host, member, room


# ---------------- 群聊消息（E1 / E2） ----------------

def test_post_message_requires_login_and_membership(client, db):
    assert client.post("/api/rooms/room_x/messages", json={"body": "hi"}).status_code == 401

    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    outsider = register_user(db, "路人")
    login(client, outsider)
    denied = client.post(f"/api/rooms/{room['id']}/messages", json={"body": "hi"})
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "FORBIDDEN"


def test_post_and_list_messages(client, db):
    host, member, room = setup_room(client, db)

    login(client, member)
    created = client.post(f"/api/rooms/{room['id']}/messages", json={"body": "  我先补充一句  "})
    assert created.status_code == 201, created.text
    message = created.json()["data"]["message"]
    assert message["body"] == "我先补充一句"          # trim
    assert message["displayName"] == "成员"
    assert message["kind"] == "chat"

    login(client, host)
    listed = client.get(f"/api/rooms/{room['id']}/messages", params={"limit": 50})
    assert listed.status_code == 200
    bodies = [item["body"] for item in listed.json()["data"]["messages"]]
    assert "我先补充一句" in bodies

    # 时间正序（最后一条是刚发的）
    assert bodies[-1] == "我先补充一句"


def test_post_message_validation(client, db):
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)

    blank = client.post(f"/api/rooms/{room['id']}/messages", json={"body": "   "})
    assert blank.status_code == 400
    assert blank.json()["error"]["code"] == "VALIDATION"

    too_long = client.post(f"/api/rooms/{room['id']}/messages", json={"body": "x" * 501})
    assert too_long.status_code == 400

    bad_cursor = client.get(f"/api/rooms/{room['id']}/messages", params={"before": "msg_not_here"})
    assert bad_cursor.status_code == 400


def test_pagination_with_before(client, db):
    host, member, room = setup_room(client, db)
    login(client, member)
    ids = []
    for index in range(3):
        resp = client.post(f"/api/rooms/{room['id']}/messages", json={"body": f"第{index}条"})
        assert resp.status_code == 201
        ids.append(resp.json()["data"]["message"]["id"])

    login(client, host)
    first_page = client.get(f"/api/rooms/{room['id']}/messages", params={"limit": 2}).json()["data"]["messages"]
    assert len(first_page) == 2
    oldest_id = first_page[0]["id"]
    second_page = client.get(
        f"/api/rooms/{room['id']}/messages", params={"limit": 2, "before": oldest_id}
    ).json()["data"]["messages"]
    assert all(item["id"] not in {m["id"] for m in first_page} for item in second_page)


def test_post_message_after_end_conflicts(client, db):
    host, member, room = setup_room(client, db)
    login(client, host)
    assert client.post(f"/api/rooms/{room['id']}/end").status_code == 200
    after = client.post(f"/api/rooms/{room['id']}/messages", json={"body": "还在吗"})
    assert after.status_code == 409
    assert after.json()["error"]["code"] == "ROOM_ENDED"


# ---------------- 举手（E3 / E5） ----------------

def test_hand_raise_is_idempotent_and_lowerable(client, db):
    host, member, room = setup_room(client, db)

    login(client, member)
    first = client.post(f"/api/rooms/{room['id']}/hand-raise")
    assert first.status_code == 200
    assert len(first.json()["data"]["hands"]) == 1

    again = client.post(f"/api/rooms/{room['id']}/hand-raise")
    assert len(again.json()["data"]["hands"]) == 1        # 幂等

    mine = client.delete(f"/api/rooms/{room['id']}/hand-raise")
    assert mine.status_code == 200 and mine.json()["data"]["hands"] == []

    # 房主放下他人
    client.post(f"/api/rooms/{room['id']}/hand-raise")
    login(client, host)
    lowered = client.delete(f"/api/rooms/{room['id']}/hand-raise/{member.id}")
    assert lowered.status_code == 200 and lowered.json()["data"]["hands"] == []

    # 目标没在举 → 400
    nothing = client.delete(f"/api/rooms/{room['id']}/hand-raise/{member.id}")
    assert nothing.status_code == 400


def test_lower_other_hand_requires_manager(client, db):
    host, member, room = setup_room(client, db)
    other = register_user(db, "另一位")
    join_as_member(client, host, room["id"], other)

    login(client, other)
    client.post(f"/api/rooms/{room['id']}/hand-raise")
    login(client, member)
    denied = client.delete(f"/api/rooms/{room['id']}/hand-raise/{other.id}")
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "FORBIDDEN"


def test_end_room_clears_active_hands(client, db):
    host, member, room = setup_room(client, db)
    login(client, member)
    client.post(f"/api/rooms/{room['id']}/hand-raise")

    login(client, host)
    assert client.post(f"/api/rooms/{room['id']}/end").status_code == 200

    rows = db.execute(
        "SELECT lowered_reason FROM room_hand_raises WHERE room_id = %s", (room["id"],)
    ).fetchall()
    assert rows and all(row[0] == "room_ended" for row in rows)


# ---------------- 焦点（E4） ----------------

def test_focus_set_clear_and_permissions(client, db):
    host, member, room = setup_room(client, db)

    login(client, host)
    set_to_member = client.post(f"/api/rooms/{room['id']}/focus", json={"userId": member.id})
    assert set_to_member.status_code == 200
    focus = set_to_member.json()["data"]["focus"]
    assert focus["subjectUserId"] == member.id and focus["subjectName"] == "成员"

    visible = client.get(f"/api/rooms/{room['id']}/focus")
    assert visible.json()["data"]["focus"]["subjectUserId"] == member.id

    cleared = client.post(f"/api/rooms/{room['id']}/focus", json={"userId": None})
    assert cleared.status_code == 200 and cleared.json()["data"]["focus"]["subjectUserId"] is None

    login(client, member)
    denied = client.post(f"/api/rooms/{room['id']}/focus", json={"userId": member.id})
    assert denied.status_code == 403

    login(client, host)
    outsider = register_user(db, "路人")
    bad_target = client.post(f"/api/rooms/{room['id']}/focus", json={"userId": outsider.id})
    assert bad_target.status_code == 400


def test_read_endpoints_require_member(client, db):
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    outsider = register_user(db, "路人")
    login(client, outsider)
    for path in ("messages", "hand-raises", "focus"):
        resp = client.get(f"/api/rooms/{room['id']}/{path}")
        assert resp.status_code == 403, path
