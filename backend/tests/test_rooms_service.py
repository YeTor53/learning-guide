"""房间模块服务层用例：建房、申请、批准/拒绝、离开、结束的规则与连带动作。

设计事实源：docs/02-modules/r001-rooms.md §4（规则表）、§9（验证矩阵）
"""
from __future__ import annotations

import pytest

from app.api.errors import AppError
from app.repositories import rooms as repo
from app.schemas.rooms import CreateRoomIn, JoinRequestIn
from app.services import rooms as rooms_service
from helpers import register_user


def _make_room(conn, host, capacity: int | None = None, title: str = "线性代数自习室"):
    created = rooms_service.create_room(
        conn, host, CreateRoomIn(topic="math-biology", topicLabel="生物学", title=title, description="面向跨专业同学")
    )
    if capacity is not None:  # 需要提前满员的用例：直接改库里的 capacity（校验允许 2~8）
        conn.execute("UPDATE rooms SET capacity = %s WHERE id = %s", (capacity, created.id))
    return created


def _join(conn, user, room_id):
    return rooms_service.request_join(conn, user, room_id, "想参加")


# ---------- 建房 ----------

def test_create_room_writes_room_and_host_member(db) -> None:
    host = register_user(db, "房主甲")
    room = _make_room(db, host)
    assert room.my_role == "host" and room.phase == "active.idle"
    assert room.member_count == 1 and room.pending_count == 0
    roles = db.execute("SELECT role, status FROM room_members WHERE room_id = %s", (room.id,)).fetchall()
    assert roles == [("host", "active")]
    assert len(room.room_code) == 6


def test_create_room_rejects_unknown_topic(db) -> None:
    host = register_user(db)
    with pytest.raises(Exception):  # Pydantic 校验失败（路由层会翻成 400 VALIDATION）
        CreateRoomIn(topic="not-a-topic", topicLabel="x", title="y")


# ---------- 申请 ----------

def test_request_join_and_duplicate(db) -> None:
    host = register_user(db, "房主甲")
    guest = register_user(db, "申请人乙")
    room = _make_room(db, host)

    created = _join(db, guest, room.id)
    assert created.status == "pending" and created.display_name == "申请人乙"

    with pytest.raises(AppError) as exc:
        _join(db, guest, room.id)
    assert (exc.value.code, exc.value.status) == ("ALREADY_PENDING", 409)


def test_request_join_rejected_when_room_ended(db) -> None:
    host = register_user(db, "房主甲")
    guest = register_user(db, "申请人乙")
    room = _make_room(db, host)
    rooms_service.end_room(db, host, room.id)

    with pytest.raises(AppError) as exc:
        _join(db, guest, room.id)
    assert exc.value.code == "ROOM_ENDED"


def test_request_join_rejected_when_already_member(db) -> None:
    host = register_user(db, "房主甲")
    room = _make_room(db, host)
    with pytest.raises(AppError) as exc:
        _join(db, host, room.id)
    assert exc.value.code == "ALREADY_MEMBER"


def test_request_join_rejected_when_full(db) -> None:
    host = register_user(db, "房主甲")
    room = _make_room(db, host, capacity=2)
    first, second = register_user(db, "成员一"), register_user(db, "成员二")
    req = _join(db, first, room.id)
    rooms_service.approve_join_request(db, host, req.id)

    with pytest.raises(AppError) as exc:
        _join(db, second, room.id)
    assert (exc.value.code, exc.value.status) == ("ROOM_FULL", 409)


# ---------- 批准 / 拒绝 ----------

def test_approve_adds_member_and_marks_request(db) -> None:
    host = register_user(db, "房主甲")
    guest = register_user(db, "申请人乙")
    room = _make_room(db, host)
    req = _join(db, guest, room.id)

    result = rooms_service.approve_join_request(db, host, req.id)
    assert result.request.status == "approved" and result.request.decided_by == host.id
    assert result.member.role == "participant" and result.member.status == "active"

    detail = rooms_service.get_room_detail(db, host, room.id)
    assert detail.room.member_count == 2
    assert {m.display_name for m in detail.members} == {"房主甲", "申请人乙"}


def test_approve_requires_manager_role(db) -> None:
    host = register_user(db, "房主甲")
    outsider = register_user(db, "路人丙")
    guest = register_user(db, "申请人乙")
    room = _make_room(db, host)
    req = _join(db, guest, room.id)

    with pytest.raises(AppError) as exc:
        rooms_service.approve_join_request(db, outsider, req.id)
    assert (exc.value.code, exc.value.status) == ("FORBIDDEN", 403)


def test_approve_when_full_keeps_request_pending(db) -> None:
    host = register_user(db, "房主甲")
    room = _make_room(db, host, capacity=2)
    first, second = register_user(db, "成员一"), register_user(db, "成员二")
    waiting = _join(db, second, room.id)          # 先让第二条申请排上队（此时还差一个名额）
    approved = _join(db, first, room.id)
    rooms_service.approve_join_request(db, host, approved.id)  # 批准后房间满

    with pytest.raises(AppError) as exc:
        rooms_service.approve_join_request(db, host, waiting.id)
    assert exc.value.code == "ROOM_FULL"
    status = db.execute("SELECT status FROM join_requests WHERE id = %s", (waiting.id,)).fetchone()[0]
    assert status == "pending"


def test_approve_twice_returns_conflict(db) -> None:
    host = register_user(db, "房主甲")
    guest = register_user(db, "申请人乙")
    room = _make_room(db, host)
    req = _join(db, guest, room.id)
    rooms_service.approve_join_request(db, host, req.id)

    with pytest.raises(AppError) as exc:
        rooms_service.approve_join_request(db, host, req.id)
    assert (exc.value.code, exc.value.status) == ("CONFLICT", 409)


def test_reject_then_can_request_again(db) -> None:
    host = register_user(db, "房主甲")
    guest = register_user(db, "申请人乙")
    room = _make_room(db, host)
    req = _join(db, guest, room.id)

    rejected = rooms_service.reject_join_request(db, host, req.id)
    assert rejected.status == "rejected"

    again = _join(db, guest, room.id)
    assert again.status == "pending"


def test_withdraw_join_request_allows_reapply(db) -> None:
    host = register_user(db, "房主甲")
    guest = register_user(db, "申请人乙")
    room = _make_room(db, host)
    request = _join(db, guest, room.id)

    withdrawn = rooms_service.withdraw_join_request(db, guest, request.id)
    assert withdrawn.status == "withdrawn" and withdrawn.decided_by == guest.id

    assert _join(db, guest, room.id).status == "pending"  # 撤回后可立即再申请
    with pytest.raises(AppError) as exc:
        rooms_service.withdraw_join_request(db, guest, request.id)  # 已处理过的申请不能再撤回
    assert (exc.value.code, exc.value.status) == ("CONFLICT", 409)


def test_withdraw_requires_owner(db) -> None:
    host = register_user(db, "房主甲")
    guest = register_user(db, "申请人乙")
    outsider = register_user(db, "路人丙")
    room = _make_room(db, host)
    request = _join(db, guest, room.id)

    with pytest.raises(AppError) as exc:
        rooms_service.withdraw_join_request(db, outsider, request.id)
    assert (exc.value.code, exc.value.status) == ("FORBIDDEN", 403)


# ---------- 离开 ----------

def test_leave_room_marks_self_leave(db) -> None:
    host = register_user(db, "房主甲")
    guest = register_user(db, "申请人乙")
    room = _make_room(db, host)
    req = _join(db, guest, room.id)
    rooms_service.approve_join_request(db, host, req.id)

    rooms_service.leave_room(db, guest, room.id)
    row = db.execute(
        "SELECT status, exit_reason FROM room_members WHERE room_id = %s AND user_id = %s", (room.id, guest.id)
    ).fetchone()
    assert row == ("inactive", "self_leave")


def test_host_cannot_leave(db) -> None:
    host = register_user(db, "房主甲")
    room = _make_room(db, host)
    with pytest.raises(AppError) as exc:
        rooms_service.leave_room(db, host, room.id)
    assert (exc.value.code, exc.value.status) == ("HOST_CANNOT_LEAVE", 409)


def test_non_member_cannot_leave(db) -> None:
    host = register_user(db, "房主甲")
    outsider = register_user(db, "路人丙")
    room = _make_room(db, host)
    with pytest.raises(AppError) as exc:
        rooms_service.leave_room(db, outsider, room.id)
    assert exc.value.code == "NOT_MEMBER"


# ---------- 结束房间 ----------

def test_end_room_cascades(db) -> None:
    host = register_user(db, "房主甲")
    guest = register_user(db, "申请人乙")
    waiting = register_user(db, "申请人丙")
    room = _make_room(db, host)
    approved = _join(db, guest, room.id)
    rooms_service.approve_join_request(db, host, approved.id)
    _join(db, waiting, room.id)

    ended = rooms_service.end_room(db, host, room.id)
    assert ended.status == "ended" and ended.ended_at is not None

    room_row = db.execute("SELECT status, ended_at FROM rooms WHERE id = %s", (room.id,)).fetchone()
    assert room_row[0] == "ended" and room_row[1] is not None
    members = db.execute(
        "SELECT status, exit_reason FROM room_members WHERE room_id = %s ORDER BY joined_at", (room.id,)
    ).fetchall()
    assert members == [("inactive", "room_ended"), ("inactive", "room_ended")]
    requests = db.execute("SELECT status, decided_by FROM join_requests WHERE room_id = %s", (room.id,)).fetchall()
    assert ("cancelled", None) in requests


def test_end_room_requires_host(db) -> None:
    host = register_user(db, "房主甲")
    guest = register_user(db, "申请人乙")
    room = _make_room(db, host)
    req = _join(db, guest, room.id)
    rooms_service.approve_join_request(db, host, req.id)

    with pytest.raises(AppError) as exc:
        rooms_service.end_room(db, guest, room.id)
    assert (exc.value.code, exc.value.status) == ("FORBIDDEN", 403)


def test_end_room_twice_returns_room_ended(db) -> None:
    host = register_user(db, "房主甲")
    room = _make_room(db, host)
    rooms_service.end_room(db, host, room.id)
    with pytest.raises(AppError) as exc:
        rooms_service.end_room(db, host, room.id)
    assert exc.value.code == "ROOM_ENDED"


# ---------- 列表与详情 ----------

def test_list_rooms_filters_and_aggregates(db) -> None:
    host = register_user(db, "房主甲")
    guest = register_user(db, "申请人乙")
    active_room = _make_room(db, host, title="进行中的房间")
    ended_room = _make_room(db, host, title="已结束的房间")
    rooms_service.end_room(db, host, ended_room.id)
    req = _join(db, guest, active_room.id)

    active_items, active_total = rooms_service.list_rooms(db, None, repo.RoomFilter(status="active"))
    titles = {item.title for item in active_items}
    assert "进行中的房间" in titles and "已结束的房间" not in titles
    assert active_total == len(active_items)
    guest_view = next(i for i in active_items if i.id == active_room.id)
    assert guest_view.pending_count == 0 and guest_view.my_role is None  # 非管理者：服务端严格返回 0（FQ-4）
    host_view = next(
        i for i in rooms_service.list_rooms(db, host, repo.RoomFilter(status="active"))[0] if i.id == active_room.id
    )
    assert host_view.pending_count == 1 and host_view.my_role == "host"

    ended_items, _ = rooms_service.list_rooms(db, None, repo.RoomFilter(status="ended"))
    ended_titles = {item.title for item in ended_items}
    assert "已结束的房间" in ended_titles
    assert "进行中的房间" not in ended_titles  # 库里还有种子里的已结束房间，故用包含关系断言

    applier_items, _ = rooms_service.list_rooms(db, guest, repo.RoomFilter(mine_user_id=guest.id))
    assert active_room.id in {i.id for i in applier_items}
    assert next(i for i in applier_items if i.id == active_room.id).my_request_status == "pending"

    host_items, _ = rooms_service.list_rooms(db, host, repo.RoomFilter(mine_user_id=host.id))
    assert {i.my_role for i in host_items if i.id == active_room.id} == {"host"}

    rooms_service.approve_join_request(db, host, req.id)
    after, _ = rooms_service.list_rooms(db, host, repo.RoomFilter(status="active", topic="math-biology"))
    assert next(i for i in after if i.id == active_room.id).member_count == 2


def test_room_detail_lists_members_and_recent_messages(db) -> None:
    host = register_user(db, "房主甲")
    room = _make_room(db, host)
    for index in range(25):
        db.execute(
            "INSERT INTO chat_messages (id, room_id, user_id, body, created_at) VALUES (%s, %s, %s, %s, now() + %s)",
            (f"msg_t{index:03d}", room.id, host.id, f"第 {index} 条", f"{index} seconds"),
        )
    detail = rooms_service.get_room_detail(db, host, room.id)
    assert len(detail.messages) == 20
    assert detail.messages[-1].body == "第 24 条"  # 升序返回，取的是最近 20 条
    assert detail.messages[0].body == "第 5 条"


def test_room_detail_not_found(db) -> None:
    with pytest.raises(AppError) as exc:
        rooms_service.get_room_detail(db, None, "room_not_exists")
    assert exc.value.code == "NOT_FOUND"


def test_ended_room_detail_includes_inactive_members(db) -> None:
    host = register_user(db, "房主甲")
    guest = register_user(db, "申请人乙")
    room = _make_room(db, host)
    req = _join(db, guest, room.id)
    rooms_service.approve_join_request(db, host, req.id)
    rooms_service.end_room(db, host, room.id)

    detail = rooms_service.get_room_detail(db, None, room.id)
    assert {m.status for m in detail.members} == {"inactive"}
    assert {m.exit_reason for m in detail.members} == {"room_ended"}


def test_derive_room_phase(db) -> None:
    host = register_user(db, "房主甲")
    room = _make_room(db, host)
    assert rooms_service.derive_room_phase(db, room.id) == "active.idle"
    rooms_service.end_room(db, host, room.id)
    assert rooms_service.derive_room_phase(db, room.id) == "ended"
