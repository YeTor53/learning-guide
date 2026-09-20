"""r013 用例：结束房回看（`/rooms/{id}/replay` 页面所依赖的三条只读接口的可见性）。

口径（需求单 §10 Q1=1）：房主 / 历史协管 / 超管 / **当时在册成员**（含已离开）可读；
不在名册的登录用户 → 403；未登录 → 401（时间线/纪要）。
页面本身是纯前端（`frontend/src/pages/ReplayPage.tsx`），这里钉住它依赖的接口口径。
"""
from __future__ import annotations

from helpers import register_user, session_cookie

TOPIC = {"topic": "custom", "topicLabel": "回看", "title": "回看用例房", "description": ""}


def login(client, user) -> None:
    name, value = session_cookie(user.id)
    client.cookies.set(name, value)


def logout(client) -> None:
    client.cookies.clear()


def create_room(client) -> dict:
    resp = client.post("/api/rooms", json=TOPIC)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def request_join(client, room_id: str) -> str:
    """（以申请人身份）提交申请，返回 request id。"""
    created = client.post(f"/api/rooms/{room_id}/join-requests", json={"message": "想参加"})
    assert created.status_code == 201, created.text
    return created.json()["data"]["id"]


def setup_ended_room(client, db) -> dict:
    """房主建房 → 申请人获批 → 房主结束房间（每步都用**对的账号**调用，403 就是真问题）。"""
    host = register_user(db, "回看房主")
    member = register_user(db, "回看成员")
    outsider = register_user(db, "路人")

    login(client, host)
    room = create_room(client)
    logout(client)

    login(client, member)
    request_id = request_join(client, room["id"])
    logout(client)

    login(client, host)
    approved = client.post(f"/api/join-requests/{request_id}/approve")
    assert approved.status_code == 200, approved.text
    ended = client.post(f"/api/rooms/{room['id']}/end")
    assert ended.status_code == 200, ended.text
    logout(client)
    return {"host": host, "member": member, "outsider": outsider, "room_id": room["id"]}


def test_member_can_replay_ended_room(client, db) -> None:
    ctx = setup_ended_room(client, db)
    login(client, ctx["member"])
    detail = client.get(f"/api/rooms/{ctx['room_id']}")
    assert detail.status_code == 200
    assert detail.json()["data"]["room"]["status"] == "ended"
    assert client.get(f"/api/rooms/{ctx['room_id']}/conversation").status_code == 200
    assert client.get(f"/api/rooms/{ctx['room_id']}/summary").status_code == 200


def test_host_and_superadmin_can_replay(client, db) -> None:
    ctx = setup_ended_room(client, db)
    login(client, ctx["host"])
    assert client.get(f"/api/rooms/{ctx['room_id']}/conversation").status_code == 200

    from helpers import session_cookie as _cookie  # 超管：seed 内置演示账号（r012 迁移 012）

    logout(client)
    from app.repositories import users as users_repo

    admin = users_repo.get_user_by_email(db, "admin@example.com")
    assert admin is not None, "演示超管应存在于 seed"
    name, value = _cookie(admin.id)
    client.cookies.set(name, value)
    assert client.get(f"/api/rooms/{ctx['room_id']}/conversation").status_code == 200
    assert client.get(f"/api/rooms/{ctx['room_id']}/summary").status_code == 200


def test_outsider_cannot_read_history(client, db) -> None:
    ctx = setup_ended_room(client, db)
    login(client, ctx["outsider"])
    # 房间详情是公开的（列表页要能显示已结束的房），但历史内容不给看
    assert client.get(f"/api/rooms/{ctx['room_id']}").status_code == 200
    line = client.get(f"/api/rooms/{ctx['room_id']}/conversation")
    assert line.status_code == 403, line.text
    assert "成员" in line.json()["error"]["message"]
    assert client.get(f"/api/rooms/{ctx['room_id']}/summary").status_code == 403


def test_anonymous_cannot_read_history(client, db) -> None:
    ctx = setup_ended_room(client, db)
    logout(client)
    assert client.get(f"/api/rooms/{ctx['room_id']}/conversation").status_code == 401
    assert client.get(f"/api/rooms/{ctx['room_id']}/summary").status_code == 401
