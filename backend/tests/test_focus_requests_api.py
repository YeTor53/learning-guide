"""r009 协管焦点申请用例（真实 PostgreSQL 回滚事务；不联网）。"""
from __future__ import annotations

from helpers import register_user, session_cookie

TOPIC = {"topic": "custom", "topicLabel": "焦点", "title": "焦点房", "description": ""}


def login(client, user) -> None:
    name, value = session_cookie(user.id)
    client.cookies.set(name, value)


def setup_room(client, db, *, moderators: int = 1):
    """房主 + N 个协管 + 1 个参与者，返回 (room, moderator_users, participant)。"""
    host = register_user(db, "房主")
    login(client, host)
    room = client.post("/api/rooms", json=TOPIC).json()["data"]
    mods = []
    for index in range(moderators):
        mod = register_user(db, f"协管{index + 1}")
        # 直接写入在册成员（测试装置）：协管身份
        db.execute(
            "INSERT INTO room_members (id, room_id, user_id, role) VALUES (%s, %s, %s, 'moderator')",
            (f"mem_mod_{index}_{room['id'][-6:]}", room["id"], mod.id),
        )
        mods.append(mod)
    guest = register_user(db, "参与者")
    db.execute(
        "INSERT INTO room_members (id, room_id, user_id, role) VALUES (%s, %s, %s, 'participant')",
        (f"mem_guest_{room['id'][-6:]}", room["id"], guest.id),
    )
    return room, host, mods, guest


def test_moderator_requests_and_self_approval_is_blocked(client, db) -> None:
    room, host, mods, _ = setup_room(client, db)
    mod = mods[0]

    # 协管申请
    login(client, mod)
    created = client.post(f"/api/rooms/{room['id']}/focus-requests")
    assert created.status_code == 201, created.text
    request_id = created.json()["data"]["id"]
    assert created.json()["data"]["status"] == "pending"
    assert created.json()["data"]["requesterName"] == "协管1"

    # 幂等：再点一次拿到同一条
    again = client.post(f"/api/rooms/{room['id']}/focus-requests")
    assert again.status_code == 201 and again.json()["data"]["id"] == request_id

    # 本人批准 → 403 SELF_APPROVAL
    blocked = client.post(f"/api/focus-requests/{request_id}/approve")
    assert blocked.status_code == 403, blocked.text
    assert blocked.json()["error"]["code"] == "SELF_APPROVAL"

    # 房主看得到待批
    login(client, host)
    listed = client.get(f"/api/rooms/{room['id']}/focus-requests")
    assert listed.status_code == 200 and len(listed.json()["data"]["requests"]) == 1


def test_host_approval_sets_focus_and_lowers_hand(client, db) -> None:
    room, host, mods, _ = setup_room(client, db)
    mod = mods[0]

    login(client, mod)
    request_id = client.post(f"/api/rooms/{room['id']}/focus-requests").json()["data"]["id"]
    client.post(f"/api/rooms/{room['id']}/hand-raise")  # 举手（申请焦点时往往同时举手）

    login(client, host)
    approved = client.post(f"/api/focus-requests/{request_id}/approve")
    assert approved.status_code == 200, approved.text
    assert approved.json()["data"]["status"] == "approved"

    focus = client.get(f"/api/rooms/{room['id']}/focus").json()["data"]["focus"]
    assert focus["subjectUserId"] == mod.id
    hands = client.get(f"/api/rooms/{room['id']}/hand-raises").json()["data"]["hands"]
    assert hands == [], f"批准后应清掉申请人的举手：{hands}"
    assert client.get(f"/api/rooms/{room['id']}/focus-requests").json()["data"]["requests"] == []


def test_reject_keeps_focus_unchanged(client, db) -> None:
    room, host, mods, _ = setup_room(client, db)
    mod = mods[0]
    login(client, mod)
    request_id = client.post(f"/api/rooms/{room['id']}/focus-requests").json()["data"]["id"]

    login(client, host)
    rejected = client.post(f"/api/focus-requests/{request_id}/reject")
    assert rejected.status_code == 200 and rejected.json()["data"]["status"] == "rejected"
    focus = client.get(f"/api/rooms/{room['id']}/focus").json()["data"]["focus"]
    assert focus.get("subjectUserId") in (None, "") , focus


def test_rules_for_host_and_participant(client, db) -> None:
    room, host, _, guest = setup_room(client, db)

    # 房主：应直接用「取得焦点」，申请被拒（400）
    login(client, host)
    as_host = client.post(f"/api/rooms/{room['id']}/focus-requests")
    assert as_host.status_code == 400 and as_host.json()["error"]["code"] == "VALIDATION"

    # 参与者：无权申请（403）
    login(client, guest)
    as_guest = client.post(f"/api/rooms/{room['id']}/focus-requests")
    assert as_guest.status_code == 403
