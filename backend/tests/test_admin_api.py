"""r012 用例：管理后台（三列表 + 三动作 + 审计）。

口径来源：docs/rounds/r012-superadmin-console/design.md §3、需求单 §10.1（Q5=1 / Q6=1 / Q7=1 / Q16=1）。
约定：LLM 与 LiveKit 一律打桩（不联网、零配额）；库侧断言走真实 PostgreSQL 的回滚事务。
"""
from __future__ import annotations

import pytest

from app.repositories import rooms as rooms_repo
from app.repositories import users as users_repo
from app.services import livekit as livekit_service
from app.services import summary as summary_service
from app.services.roles import SUPERADMIN
from helpers import register_user, session_cookie

TOPIC = {"topic": "custom", "topicLabel": "后台", "title": "后台用例房", "description": ""}


def login(client, user) -> None:
    name, value = session_cookie(user.id)
    client.cookies.set(name, value)


def create_room(client, title: str = "后台用例房") -> dict:
    resp = client.post("/api/rooms", json={**TOPIC, "title": title})
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def promote(db, user):
    assert users_repo.set_user_role(db, user.id, SUPERADMIN) == 1
    return user


def superadmin(db, client, name: str = "超管"):
    admin = promote(db, register_user(db, name))
    login(client, admin)
    return admin


def items_of(client, path: str) -> list[dict]:
    resp = client.get(path)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["items"]


# ---------------- 鉴权 ----------------

def test_all_admin_endpoints_require_superadmin(client, db) -> None:
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)

    reads = ["/api/admin/rooms", "/api/admin/users", "/api/admin/summaries", "/api/admin/audit"]
    for path in reads:
        assert client.get(path).status_code == 403, path
    writes = [
        ("post", f"/api/admin/rooms/{room['id']}/end"),
        ("delete", f"/api/admin/rooms/{room['id']}"),
        ("post", f"/api/admin/rooms/{room['id']}/summary"),
    ]
    for method, path in writes:
        call = getattr(client, method)
        assert call(path).status_code == 403, path

    client.cookies.clear()
    for path in reads:
        assert client.get(path).status_code == 401, path


# ---------------- 三列表 ----------------

def test_room_list_shows_host_counts_and_summary_status(client, db, monkeypatch) -> None:
    monkeypatch.setattr(summary_service, "call_llm", lambda messages, settings=None: "纪要正文")
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client, "后台列表房")
    guest = register_user(db, "申请人")
    login(client, guest)
    assert client.post(f"/api/rooms/{room['id']}/join-requests", json={"message": "想加入"}).status_code == 201
    login(client, host)
    client.post(f"/api/rooms/{room['id']}/summary")

    superadmin(db, client)
    rows = items_of(client, "/api/admin/rooms?status=active&q=后台列表房")
    row = next(item for item in rows if item["id"] == room["id"])
    assert row["hostName"] == host.display_name
    assert row["memberCount"] == 1
    assert row["pendingCount"] == 1
    assert row["summaryStatus"] == "ready"
    assert row["roomCode"]


def test_room_list_pagination_and_status_filter(client, db) -> None:
    host = register_user(db, "房主")
    login(client, host)
    active = create_room(client, "分页-进行中")
    ended = create_room(client, "分页-已结束")
    assert client.post(f"/api/rooms/{ended['id']}/end").status_code == 200

    superadmin(db, client)
    first_page = items_of(client, "/api/admin/rooms?q=分页&limit=1&offset=0")
    second_page = items_of(client, "/api/admin/rooms?q=分页&limit=1&offset=1")
    assert len(first_page) == 1 and len(second_page) == 1
    assert {first_page[0]["id"], second_page[0]["id"]} == {active["id"], ended["id"]}
    ended_only = items_of(client, "/api/admin/rooms?q=分页&status=ended")
    assert [item["id"] for item in ended_only] == [ended["id"]]


def test_user_list_covers_roles_heartbeat_and_online_filter(client, db) -> None:
    from datetime import datetime, timedelta, timezone

    online = register_user(db, "在线的同学")
    offline = register_user(db, "很久没动")
    login(client, online)
    assert client.post("/api/presence").status_code == 200
    users_repo.touch_last_seen(db, offline.id, datetime.now(timezone.utc) - timedelta(hours=2))

    superadmin(db, client, "后台管理")
    all_rows = items_of(client, "/api/admin/users?limit=100")
    ids = {row["id"] for row in all_rows}
    assert {online.id, offline.id} <= ids
    assert any(row["role"] == SUPERADMIN for row in all_rows)
    assert any(row["id"] == online.id and row["lastSeenAt"] for row in all_rows)

    online_only = items_of(client, "/api/admin/users?online_only=1&limit=100")
    online_ids = {row["id"] for row in online_only}
    assert online.id in online_ids
    assert offline.id not in online_ids


def test_summary_list_and_audit_start_empty(client, db, monkeypatch) -> None:
    monkeypatch.setattr(summary_service, "call_llm", lambda messages, settings=None: "纪要正文")
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client, "纪要列表房")
    assert client.post(f"/api/rooms/{room['id']}/summary").status_code == 201

    superadmin(db, client)
    rows = items_of(client, "/api/admin/summaries?status=ready&limit=100")
    row = next(item for item in rows if item["roomId"] == room["id"])
    assert row["roomTitle"] == "纪要列表房"
    assert row["contentLength"] == len("纪要正文")
    assert row["model"]
    assert items_of(client, "/api/admin/audit?limit=100") == []


# ---------------- 三动作 ----------------

def test_admin_end_room_writes_audit_and_system_message(client, db, monkeypatch) -> None:
    monkeypatch.setattr(livekit_service, "delete_room", lambda room, settings=None: True)
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client, "超管要结束的房")

    admin = superadmin(db, client)
    resp = client.post(f"/api/admin/rooms/{room['id']}/end")
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "ended"
    assert rooms_repo.get_room(db, room["id"]).room.status == "ended"

    audits = items_of(client, "/api/admin/audit")
    entry = next(item for item in audits if item["targetId"] == room["id"])
    assert entry["action"] == "room.end"
    assert entry["targetType"] == "room"
    assert entry["actorId"] == admin.id
    assert entry["detail"]["title"] == "超管要结束的房"
    bodies = [m.message.body for m in rooms_repo.list_recent_messages(db, room["id"], 10)]
    assert "房间已结束" in bodies


def test_admin_delete_room_is_hard_delete_but_keeps_audit(client, db, monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(livekit_service, "delete_room", lambda room, settings=None: calls.append(room) or True)
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client, "待删的房")
    assert client.post(f"/api/rooms/{room['id']}/messages", json={"body": "留个痕迹"}).status_code == 201

    superadmin(db, client)
    resp = client.delete(f"/api/admin/rooms/{room['id']}")
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"] == {"deleted": True, "livekitApplied": True}
    assert calls == [room["id"]]

    assert rooms_repo.get_room(db, room["id"]) is None
    assert client.get(f"/api/rooms/{room['id']}").status_code == 404
    messages = db.execute("SELECT count(*) FROM chat_messages WHERE room_id = %s", (room["id"],)).fetchone()[0]
    assert messages == 0

    audits = items_of(client, "/api/admin/audit?action=room.delete")
    entry = next(item for item in audits if item["targetId"] == room["id"])
    assert entry["detail"]["snapshot"]["title"] == "待删的房"
    assert entry["detail"]["snapshot"]["messageCount"] == 1


def test_admin_regenerate_summary_writes_audit(client, db, monkeypatch) -> None:
    monkeypatch.setattr(summary_service, "call_llm", lambda messages, settings=None: "超管版纪要")
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client, "超管重生纪要房")

    superadmin(db, client)
    resp = client.post(f"/api/admin/rooms/{room['id']}/summary")
    assert resp.status_code == 201, resp.text
    assert resp.json()["data"]["content"] == "超管版纪要"
    audits = items_of(client, "/api/admin/audit?action=room.summary_regenerate")
    entry = next(item for item in audits if item["targetId"] == room["id"])
    assert entry["detail"]["status"] == "ready"


def test_admin_delete_unknown_room_is_404_and_writes_no_audit(client, db) -> None:
    superadmin(db, client)
    assert client.delete("/api/admin/rooms/room_not_exists").status_code == 404
    assert client.post("/api/admin/rooms/room_not_exists/end").status_code == 404
    assert items_of(client, "/api/admin/audit") == []
