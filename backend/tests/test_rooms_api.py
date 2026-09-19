"""房间模块接口层用例：信封形状、状态码与错误码矩阵、端到端链路。

设计事实源：docs/01-architecture/r001-app-architecture.md §8（信封与错误码）、
            docs/02-modules/r001-rooms.md §5（接口清单）
"""
from __future__ import annotations

from app.security.session import COOKIE_NAME
from helpers import register_user, session_cookie


def _login_as(client, user) -> None:
    name, value = session_cookie(user.id)
    assert name == COOKIE_NAME
    client.cookies.set(name, value)


def _create_room(client, title: str = "接口层房间"):
    resp = client.post(
        "/api/rooms",
        json={"topic": "math-biology", "topicLabel": "生物学", "title": title, "description": "接口层用例"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def test_create_room_requires_login(client, db) -> None:
    resp = client.post("/api/rooms", json={"topic": "custom", "topicLabel": "自定", "title": "未登录不能建房"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_create_room_returns_vo_with_camel_case_keys(client, db) -> None:
    host = register_user(db, "接口房主")
    _login_as(client, host)
    data = _create_room(client, "接口层房间甲")
    assert data["myRole"] == "host" and data["memberCount"] == 1 and data["hostName"] == "接口房主"
    assert data["phase"] == "active.idle" and len(data["roomCode"]) == 6
    assert "member_count" not in data  # 对外一律 camelCase


def test_create_room_validation_error(client, db) -> None:
    host = register_user(db, "接口房主")
    _login_as(client, host)
    resp = client.post("/api/rooms", json={"topic": "not-a-topic", "topicLabel": "x", "title": "y"})
    assert resp.status_code == 400 and resp.json()["error"]["code"] == "VALIDATION"
    resp = client.post("/api/rooms", json={"topic": "custom", "topicLabel": "自定", "title": ""})
    assert resp.status_code == 400


def test_list_rooms_visible_to_guest_and_mine_requires_login(client, db) -> None:
    host = register_user(db, "接口房主")
    _login_as(client, host)
    room = _create_room(client, "公开可见的房间")

    client.cookies.clear()
    listing = client.get("/api/rooms")
    assert listing.status_code == 200
    body = listing.json()["data"]
    assert any(item["id"] == room["id"] for item in body["rooms"])
    assert body["total"] >= 1

    assert client.get("/api/rooms?mine=1").status_code == 401
    assert client.get("/api/rooms?status=bogus").status_code == 400


def test_room_detail_shows_members_and_my_role(client, db) -> None:
    host = register_user(db, "接口房主")
    _login_as(client, host)
    room = _create_room(client, "详情房间")
    detail = client.get(f"/api/rooms/{room['id']}")
    assert detail.status_code == 200
    body = detail.json()["data"]
    assert body["room"]["myRole"] == "host"
    assert [m["role"] for m in body["members"]] == ["host"]
    assert body["messages"] == []
    assert client.get("/api/rooms/room_missing").status_code == 404


def test_full_flow_join_approve_leave_end(client, db) -> None:
    host = register_user(db, "房主")
    guest = register_user(db, "申请人")
    _login_as(client, host)
    room = _create_room(client, "端到端房间")

    # 访客未登录提交申请 → 401
    client.cookies.clear()
    assert client.post(f"/api/rooms/{room['id']}/join-requests", json={}).status_code == 401

    # 申请人提交 → 201；重复提交 → 409 ALREADY_PENDING
    _login_as(client, guest)
    created = client.post(f"/api/rooms/{room['id']}/join-requests", json={"message": "想参加"})
    assert created.status_code == 201 and created.json()["data"]["status"] == "pending"
    dup = client.post(f"/api/rooms/{room['id']}/join-requests", json={})
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "ALREADY_PENDING"

    # 非管理者看不到申请列表 → 403
    forbidden = client.get(f"/api/rooms/{room['id']}/join-requests")
    assert forbidden.status_code == 403 and forbidden.json()["error"]["code"] == "FORBIDDEN"

    # 房主看列表并批准
    _login_as(client, host)
    listed = client.get(f"/api/rooms/{room['id']}/join-requests?status=pending")
    assert listed.status_code == 200
    requests = listed.json()["data"]["requests"]
    assert len(requests) == 1 and requests[0]["displayName"] == "申请人"
    request_id = requests[0]["id"]

    approved = client.post(f"/api/join-requests/{request_id}/approve")
    assert approved.status_code == 200
    assert approved.json()["data"]["member"]["role"] == "participant"

    detail = client.get(f"/api/rooms/{room['id']}").json()["data"]
    assert detail["room"]["memberCount"] == 2

    # 房主不能离开 → 409
    host_leave = client.post(f"/api/rooms/{room['id']}/leave")
    assert host_leave.status_code == 409 and host_leave.json()["error"]["code"] == "HOST_CANNOT_LEAVE"

    # 参与者离开 → 200，之后可再次申请
    _login_as(client, guest)
    assert client.post(f"/api/rooms/{room['id']}/leave").status_code == 200
    assert client.post(f"/api/rooms/{room['id']}/join-requests", json={}).status_code == 201

    # 房主结束房间 → 200；之后申请被拒
    _login_as(client, host)
    ended = client.post(f"/api/rooms/{room['id']}/end")
    assert ended.status_code == 200 and ended.json()["data"]["status"] == "ended"

    _login_as(client, guest)
    blocked = client.post(f"/api/rooms/{room['id']}/join-requests", json={})
    assert blocked.status_code == 409 and blocked.json()["error"]["code"] == "ROOM_ENDED"

    # 结束后详情：历史成员带退出原因；申请为 cancelled（只读）
    detail = client.get(f"/api/rooms/{room['id']}").json()["data"]
    assert detail["room"]["status"] == "ended"
    assert {m["status"] for m in detail["members"]} == {"inactive"}
    exit_by_user = {m["displayName"]: m["exitReason"] for m in detail["members"]}
    assert exit_by_user["房主"] == "room_ended"       # 随房间结束被移出
    assert exit_by_user["申请人"] == "self_leave"     # 自己先离开过，再申请未获批

    _login_as(client, host)
    all_requests = client.get(f"/api/rooms/{room['id']}/join-requests").json()["data"]["requests"]
    assert {r["status"] for r in all_requests} == {"approved", "cancelled"}


def test_pending_count_visible_only_to_managers(client, db) -> None:
    """FQ-4：待批申请数对非房主/协管（含申请人本人）服务端一律返回 0。"""
    host = register_user(db, "房主")
    guest = register_user(db, "申请人")
    _login_as(client, host)
    room = _create_room(client, "待批数房间")

    _login_as(client, guest)
    client.post(f"/api/rooms/{room['id']}/join-requests", json={})
    listing = client.get("/api/rooms").json()["data"]["rooms"]
    assert next(i for i in listing if i["id"] == room["id"])["pendingCount"] == 0
    assert client.get(f"/api/rooms/{room['id']}").json()["data"]["room"]["pendingCount"] == 0

    _login_as(client, host)
    listing = client.get("/api/rooms").json()["data"]["rooms"]
    assert next(i for i in listing if i["id"] == room["id"])["pendingCount"] == 1
    assert client.get(f"/api/rooms/{room['id']}").json()["data"]["room"]["pendingCount"] == 1


def test_withdraw_flow(client, db) -> None:
    host = register_user(db, "房主")
    guest = register_user(db, "申请人")
    _login_as(client, host)
    room = _create_room(client, "撤回流程房间")

    _login_as(client, guest)
    request_id = client.post(f"/api/rooms/{room['id']}/join-requests", json={}).json()["data"]["id"]

    withdrawn = client.post(f"/api/join-requests/{request_id}/withdraw")
    assert withdrawn.status_code == 200 and withdrawn.json()["data"]["request"]["status"] == "withdrawn"

    assert client.post(f"/api/rooms/{room['id']}/join-requests", json={}).status_code == 201  # 可再次申请
    assert client.post(f"/api/join-requests/{request_id}/withdraw").status_code == 409         # 旧申请已处理

    _login_as(client, host)
    pending = client.get(f"/api/rooms/{room['id']}/join-requests?status=pending").json()["data"]["requests"]
    assert len(pending) == 1 and pending[0]["id"] != request_id


def test_reject_flow_and_reapply(client, db) -> None:
    host = register_user(db, "房主")
    guest = register_user(db, "申请人")
    _login_as(client, host)
    room = _create_room(client, "拒绝流程房间")

    _login_as(client, guest)
    request_id = client.post(f"/api/rooms/{room['id']}/join-requests", json={}).json()["data"]["id"]

    _login_as(client, host)
    rejected = client.post(f"/api/join-requests/{request_id}/reject")
    assert rejected.status_code == 200 and rejected.json()["data"]["request"]["status"] == "rejected"

    # 再次处理同一申请 → 409 CONFLICT
    again = client.post(f"/api/join-requests/{request_id}/reject")
    assert again.status_code == 409 and again.json()["error"]["code"] == "CONFLICT"

    # 申请人可再次提交
    _login_as(client, guest)
    assert client.post(f"/api/rooms/{room['id']}/join-requests", json={}).status_code == 201


def test_approve_missing_request_returns_404(client, db) -> None:
    host = register_user(db, "房主")
    _login_as(client, host)
    assert client.post("/api/join-requests/req_missing/approve").status_code == 404

# ---------------- 偿还 r001 欠账（r002 cp-2）：列表分页 + 房间码冲突重试 ----------------

def test_list_rooms_pagination(client, db) -> None:
    """列表分页：limit/offset 生效、页间不重叠、越界页返回空数组（r001 欠账）。"""
    host = register_user(db, "分页房主")
    _login_as(client, host)
    created = {_create_room(client, f"分页房间{i}")["id"] for i in range(3)}

    page1 = client.get("/api/rooms", params={"limit": 2, "offset": 0}).json()["data"]
    assert page1["limit"] == 2 and page1["offset"] == 0
    assert len(page1["rooms"]) == 2
    assert page1["total"] >= 3

    page2 = client.get("/api/rooms", params={"limit": 2, "offset": 2}).json()["data"]
    ids1 = {r["id"] for r in page1["rooms"]}
    ids2 = {r["id"] for r in page2["rooms"]}
    assert len(ids2) >= 1
    assert not (ids1 & ids2), "相邻两页不应重叠"
    assert created <= (ids1 | ids2) | {r["id"] for r in client.get("/api/rooms", params={"limit": 100}).json()["data"]["rooms"]}

    far = client.get("/api/rooms", params={"limit": 2, "offset": 500}).json()["data"]
    assert far["rooms"] == []


def test_room_code_collision_retries_then_gives_up(client, db, monkeypatch) -> None:
    """房间码撞车：前两次冲突第三次成功；连续 3 次冲突 → 500 INTERNAL（r001 欠账）。"""
    from app.services import rooms as rooms_service

    host = register_user(db, "撞码房主")
    _login_as(client, host)
    taken = _create_room(client, "先占地")["roomCode"]

    seq = [taken, taken, "ZZZ234"]
    monkeypatch.setattr(rooms_service, "new_code", lambda: seq.pop(0))
    retried = _create_room(client, "撞两次后成功")
    assert retried["roomCode"] == "ZZZ234"

    monkeypatch.setattr(rooms_service, "new_code", lambda: taken)
    resp = client.post("/api/rooms", json={"topic": "custom", "topicLabel": "自定", "title": "必失败"})
    assert resp.status_code == 500
    assert resp.json()["error"]["code"] == "INTERNAL"


def test_new_topic_accepted_and_invalid_topic_rejected(client, db) -> None:
    """r007：主题白名单扩容到 14 项（迁移 006）；新主题可建房，非法主题 400。

    事实源：`docs/00-requirements/r007-topic-and-scrollhint.md` §3（顺序：原有 3 项在前，自定义最后）。
    """
    host = register_user(db, "主题房主")
    _login_as(client, host)

    created = client.post(
        "/api/rooms",
        json={"topic": "philosophy-history", "topicLabel": "西方哲学史", "title": "新主题房间", "description": ""},
    )
    assert created.status_code == 201, created.text
    assert created.json()["data"]["topic"] == "philosophy-history"

    bad = client.post(
        "/api/rooms",
        json={"topic": "quantum-cooking", "topicLabel": "非法", "title": "非法主题", "description": ""},
    )
    assert bad.status_code == 400, bad.text

    # 未知主题筛选同 400（走 TOPICS 校验）
    filtered = client.get("/api/rooms", params={"topic": "quantum-cooking"})
    assert filtered.status_code == 400, filtered.text
