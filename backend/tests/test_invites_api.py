"""r008 限时邀请用例（真实 PostgreSQL 回滚事务；不联网）。

设计事实源：`docs/rounds/r008-assignment-gaps/design.md` §2.7；决定见 ADR-0019。
口径：有效期最长 1 分钟（默认 60 秒）、默认 1 次可用；过期/用尽/非法 → 400 `INVITE_INVALID`；满员 → 409 `ROOM_FULL`。
"""
from __future__ import annotations

import pytest

from helpers import register_user, session_cookie

TOPIC = {"topic": "custom", "topicLabel": "邀请", "title": "邀请房", "description": ""}


def login(client, user) -> None:
    name, value = session_cookie(user.id)
    client.cookies.set(name, value)


def create_room(client, title: str = "邀请房") -> dict:
    resp = client.post("/api/rooms", json={**TOPIC, "title": title})
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def test_create_invite_requires_manager(client, db) -> None:
    host = register_user(db, "房主")
    outsider = register_user(db, "外人")
    login(client, host)
    room = create_room(client)

    login(client, outsider)
    resp = client.post(f"/api/rooms/{room['id']}/invites", json={"ttlSeconds": 30, "maxUses": 1})
    assert resp.status_code == 403, resp.text


def test_create_invite_ttl_capped_and_validated(client, db) -> None:
    """用户口径：有效期最长 1 分钟 —— 61 秒要 400，30 秒正常。"""
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)

    too_long = client.post(f"/api/rooms/{room['id']}/invites", json={"ttlSeconds": 61, "maxUses": 1})
    assert too_long.status_code == 400, too_long.text
    assert too_long.json()["error"]["code"] == "VALIDATION"

    ok = client.post(f"/api/rooms/{room['id']}/invites", json={"ttlSeconds": 30, "maxUses": 1})
    assert ok.status_code == 201, ok.text
    data = ok.json()["data"]
    assert len(data["code"]) == 6 and data["code"].islower()
    assert data["maxUses"] == 1 and data["usedCount"] == 0 and data["expired"] is False


def test_accept_by_code_joins_directly_and_is_idempotent(client, db) -> None:
    host = register_user(db, "房主")
    guest = register_user(db, "客人")
    login(client, host)
    room = create_room(client)
    code = client.post(f"/api/rooms/{room['id']}/invites", json={"ttlSeconds": 60, "maxUses": 1}).json()["data"]["code"]

    login(client, guest)
    joined = client.post(f"/api/invites/{code}/accept")
    assert joined.status_code == 201, joined.text
    assert joined.json()["data"]["created"] is True
    assert joined.json()["data"]["roomId"] == room["id"]

    detail = client.get(f"/api/rooms/{room['id']}").json()["data"]
    assert detail["room"]["myRole"] == "participant"
    bodies = [m["body"] for m in detail["messages"] if m["kind"] == "system"]
    assert any("通过邀请链接加入" in body for body in bodies), bodies

    # 幂等：同一个人再来一次 → 200 且不再消耗次数
    again = client.post(f"/api/invites/{code}/accept")
    assert again.status_code == 200, again.text
    assert again.json()["data"]["created"] is False
    cur = db.execute("SELECT used_count FROM invites WHERE lower(code) = lower(%s)", (code,))
    assert cur.fetchone()[0] == 1


def test_invite_invalid_expired_exhausted(client, db) -> None:
    host = register_user(db, "房主")
    guest = register_user(db, "客人")
    other = register_user(db, "后来者")
    login(client, host)
    room = create_room(client)
    code = client.post(f"/api/rooms/{room['id']}/invites", json={"ttlSeconds": 60, "maxUses": 1}).json()["data"]["code"]

    # 乱码
    login(client, guest)
    bad = client.post("/api/invites/NOPE01/accept")
    assert bad.status_code == 400 and bad.json()["error"]["code"] == "INVITE_INVALID"

    # 用尽（guest 用掉唯一一次后，other 再来）
    assert client.post(f"/api/invites/{code}/accept").status_code in (200, 201)
    login(client, other)
    used = client.post(f"/api/invites/{code}/accept")
    assert used.status_code == 400 and used.json()["error"]["code"] == "INVITE_INVALID"

    # 过期
    login(client, host)
    second = client.post(f"/api/rooms/{room['id']}/invites", json={"ttlSeconds": 30, "maxUses": 5}).json()["data"]["code"]
    db.execute("UPDATE invites SET expires_at = clock_timestamp() - interval '1 second' WHERE lower(code) = lower(%s)", (second,))
    login(client, other)
    expired = client.post(f"/api/invites/{second}/accept")
    assert expired.status_code == 400 and expired.json()["error"]["code"] == "INVITE_INVALID"


def test_full_room_blocks_invite_join(client, db) -> None:
    """邀请不能绕过 8 人上限：满员时凭码加入 → 409 ROOM_FULL。"""
    host = register_user(db, "房主")
    guest = register_user(db, "客人")
    login(client, host)
    room = create_room(client)
    code = client.post(f"/api/rooms/{room['id']}/invites", json={"ttlSeconds": 60, "maxUses": 5}).json()["data"]["code"]

    # 直接把在册成员填到上限（测试装置；容量闸只数在册行）
    for i in range(room["capacity"] - 1):
        filler = register_user(db, f"填充{i + 1}")
        db.execute(
            "INSERT INTO room_members (id, room_id, user_id, role) VALUES (%s, %s, %s, 'participant')",
            (f"mem_fill_{i}_{room['id'][-6:]}", room["id"], filler.id),
        )

    login(client, guest)
    full = client.post(f"/api/invites/{code}/accept")
    assert full.status_code == 409, full.text
    assert full.json()["error"]["code"] == "ROOM_FULL"
