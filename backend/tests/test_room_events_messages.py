"""r005 接口/服务层用例：房间事件写系统消息（`kind='system'`）。

设计事实源：`docs/rounds/r005-fix-capacity/design.md` §4（文案表）、需求单 E5。
约定：库侧断言走真实 PostgreSQL（conftest 的回滚事务，跑完不留数据）。
"""
from __future__ import annotations

from app.services import rooms as rooms_service
from app.schemas.rooms import CreateRoomIn, JoinRequestIn
from helpers import register_user, session_cookie

TOPIC = {"topic": "custom", "topicLabel": "测试主题", "title": "测试房间", "description": ""}


def login(client, user) -> None:
    name, value = session_cookie(user.id)
    client.cookies.set(name, value)


def create_room(client, title: str = "测试房间") -> dict:
    resp = client.post("/api/rooms", json={**TOPIC, "title": title})
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def system_bodies(db, room_id: str) -> list[str]:
    rows = db.execute(
        "SELECT body FROM chat_messages WHERE room_id = %s AND kind = 'system' ORDER BY created_at, id", (room_id,)
    ).fetchall()
    return [row[0] for row in rows]


def join_as_member(client, host, room_id: str, applicant) -> str:
    login(client, applicant)
    created = client.post(f"/api/rooms/{room_id}/join-requests", json={"message": "想加入"})
    assert created.status_code == 201, created.text
    request_id = created.json()["data"]["id"]
    login(client, host)
    approved = client.post(f"/api/join-requests/{request_id}/approve")
    assert approved.status_code == 200, approved.text
    return applicant.id


def test_join_and_leave_leave_system_messages(client, db) -> None:
    host = register_user(db, "房主")
    guest = register_user(db, "申请人")
    login(client, host)
    room = create_room(client)
    join_as_member(client, host, room["id"], guest)
    assert "申请人 加入了房间" in system_bodies(db, room["id"])

    login(client, guest)
    assert client.post(f"/api/rooms/{room['id']}/leave").status_code == 200
    bodies = system_bodies(db, room["id"])
    assert "申请人 离开了房间" in bodies


def test_kick_and_transfer_and_end_leave_system_messages(client, db) -> None:
    host = register_user(db, "房主")
    member = register_user(db, "成员")
    login(client, host)
    room = create_room(client)
    join_as_member(client, host, room["id"], member)

    # 移交房主 → 「X 成为房主」
    assert client.post(f"/api/rooms/{room['id']}/transfer-host", json={"userId": member.id}).status_code == 200
    assert "成员 成为房主" in system_bodies(db, room["id"])

    # 新房主把原房主移出 → 「X 被移出房间」
    login(client, member)
    assert client.delete(f"/api/rooms/{room['id']}/members/{host.id}").status_code == 200
    assert "房主 被移出房间" in system_bodies(db, room["id"])

    # 结束房间 → 「房间已结束」
    assert client.post(f"/api/rooms/{room['id']}/end").status_code == 200
    assert "房间已结束" in system_bodies(db, room["id"])


def test_full_room_rejection_leaves_system_message(client, db) -> None:
    """满员拒绝也要留痕（Q3），且消息不能被 409 的回滚带走。"""
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    db.execute("UPDATE rooms SET capacity = 2 WHERE id = %s", (room["id"],))
    first = register_user(db, "成员一")
    join_as_member(client, host, room["id"], first)  # 在册 2 = 满

    third = register_user(db, "第三人")
    login(client, third)
    denied = client.post(f"/api/rooms/{room['id']}/join-requests", json={"message": "想加入"})
    assert denied.status_code == 409 and denied.json()["error"]["code"] == "ROOM_FULL"
    bodies = system_bodies(db, room["id"])
    assert "房间已满（上限 2 人），本次申请未通过" in bodies, bodies


def test_system_messages_visible_in_message_list(client, db) -> None:
    """刷新后仍在消息列表里（库为准）：GET /messages 返回 `kind='system'` 行。"""
    host = register_user(db, "房主")
    guest = register_user(db, "申请人")
    login(client, host)
    room = create_room(client)
    join_as_member(client, host, room["id"], guest)

    login(client, host)
    listed = client.get(f"/api/rooms/{room['id']}/messages?limit=50")
    assert listed.status_code == 200
    messages = listed.json()["data"]["messages"]
    system = [m for m in messages if m["kind"] == "system"]
    assert any(m["body"] == "申请人 加入了房间" for m in system), messages
