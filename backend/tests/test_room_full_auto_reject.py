"""r011 用例：满员时自动拒绝该房待批申请（你 2026-09-20 拍板「在等待的自动拒绝」）。

口径来源：`docs/rounds/r011-debt-backfill/design.md` §2（B1）；ADR-0016（容量按本库在册成员）。
"""
from __future__ import annotations

from uuid import uuid4

from helpers import register_user, session_cookie

TOPIC = {"topic": "custom", "topicLabel": "容量", "title": "满员房", "description": ""}


def login(client, user) -> None:
    name, value = session_cookie(user.id)
    client.cookies.set(name, value)


def create_room(client) -> dict:
    resp = client.post("/api/rooms", json=TOPIC)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def add_member(db, room_id: str, user_id: str, role: str = "participant") -> None:
    db.execute(
        "INSERT INTO room_members (id, room_id, user_id, role) VALUES (%s, %s, %s, %s)",
        (f"mem_{uuid4().hex[:10]}", room_id, user_id, role),
    )


def add_pending(db, room_id: str, user_id: str) -> str:
    request_id = f"req_{uuid4().hex[:10]}"
    db.execute(
        "INSERT INTO join_requests (id, room_id, user_id, message) VALUES (%s, %s, %s, '')",
        (request_id, room_id, user_id),
    )
    return request_id


def fill_room(db, room: dict) -> None:
    """房主已在册 → 补到满员（容量取房间自带值，避免与 .env 的 ROOM_CAPACITY 打架）。"""
    for index in range(room["capacity"] - 1):
        user = register_user(db, f"在册{index}")
        add_member(db, room["id"], user.id)


def test_new_request_when_full_rejects_all_pending(client, db) -> None:
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    fill_room(db, room)

    waiting = [register_user(db, f"待批{index}") for index in range(2)]
    for user in waiting:
        add_pending(db, room["id"], user.id)

    outsider = register_user(db, "第九人")
    login(client, outsider)
    resp = client.post(f"/api/rooms/{room['id']}/join-requests", json={})
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "ROOM_FULL"

    statuses = db.execute(
        "SELECT status FROM join_requests WHERE room_id = %s", (room["id"],)
    ).fetchall()
    assert statuses and all(row[0] == "rejected" for row in statuses), statuses

    messages = db.execute(
        "SELECT body FROM chat_messages WHERE room_id = %s AND kind = 'system'", (room["id"],)
    ).fetchall()
    assert any("自动拒绝" in row[0] for row in messages), messages


def test_approve_when_full_also_rejects_and_survives_rollback(client, db) -> None:
    """批准被容量挡回时，待批申请**仍被清掉**（清理先提交，不被 raise 回滚）。"""
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    fill_room(db, room)

    waiting = register_user(db, "待批")
    request_id = add_pending(db, room["id"], waiting.id)

    resp = client.post(f"/api/join-requests/{request_id}/approve")
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "ROOM_FULL"

    status = db.execute("SELECT status FROM join_requests WHERE id = %s", (request_id,)).fetchone()[0]
    assert status == "rejected", status
    assert db.execute("SELECT count(*) FROM room_members WHERE room_id = %s", (room["id"],)).fetchone()[0] == room["capacity"]


def test_pending_requests_list_is_empty_after_auto_reject(client, db) -> None:
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    fill_room(db, room)
    waiting = register_user(db, "待批")
    add_pending(db, room["id"], waiting.id)

    outsider = register_user(db, "第九人")
    login(client, outsider)
    assert client.post(f"/api/rooms/{room['id']}/join-requests", json={}).status_code == 409  # 满员被拒
    login(client, host)
    listed = client.get(f"/api/rooms/{room['id']}/join-requests?status=pending")
    assert listed.status_code == 200, listed.text
    assert listed.json()["data"]["requests"] == []
