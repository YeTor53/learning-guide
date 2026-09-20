"""协管焦点申请（r009）：房主直取、协管申请—**他人**批准（ADR-0021 D2）。

设计事实源：docs/rounds/r009-focus-system/design.md §2.3
"""
from __future__ import annotations

from psycopg import Connection

from app.api.errors import ERR_SELF_APPROVAL, ERR_UNAUTHORIZED, ERR_VALIDATION, AppError
from app.repositories import focus_requests as repo
from app.repositories import room_extras as extras_repo
from app.repositories import rooms as rooms_repo
from app.schemas.auth import UserVO
from app.schemas.rooms import FocusRequestVO
from app.security.ids import new_id
from app.services import focus as focus_service
from app.services.messages import _guard_active_member
from app.services.rooms import MANAGER_ROLES, assert_room_role


def _vo(row: repo.RequestRow, requester_name: str) -> FocusRequestVO:
    return FocusRequestVO(
        id=row.id,
        room_id=row.room_id,
        requester_id=row.requester_id,
        requester_name=requester_name,
        status=row.status,
        decided_by=row.decided_by,
        created_at=row.created_at,
        decided_at=row.decided_at,
    )


def request_focus(conn: Connection, actor: UserVO, room_id: str) -> FocusRequestVO:
    """协管发起焦点申请；已在批 → 幂等返回同一条。房主请直接用「取得焦点」。"""
    with conn.transaction():
        rooms_repo.lock_room(conn, room_id)
        _guard_active_member(conn, actor, room_id)
        member = assert_room_role(conn, actor, room_id, MANAGER_ROLES)
        if member.role == "host":
            raise AppError(ERR_VALIDATION, "房主可直接取得焦点（无需申请）", status=400)
        created = repo.insert_request(conn, new_id("freq"), room_id, actor.id)
        row = created or repo.get_pending(conn, room_id, actor.id)
        if row is None:
            raise AppError(ERR_VALIDATION, "申请创建失败", status=500)
        result = _vo(row, actor.display_name)
    return result


def list_focus_requests(conn: Connection, actor: UserVO, room_id: str) -> list[FocusRequestVO]:
    """待批的焦点申请（Host/Moderator 可见）。"""
    _guard_active_member(conn, actor, room_id)
    assert_room_role(conn, actor, room_id, MANAGER_ROLES)
    return [_vo(row, row.requester_name) for row in repo.list_pending(conn, room_id)]


def decide_focus_request(conn: Connection, actor: UserVO, request_id: str, *, approve: bool) -> FocusRequestVO:
    """批准 / 拒绝。**必须**：actor 是 Host/Moderator 且 **不是申请人本人**（403 `SELF_APPROVAL`）。"""
    if actor is None:
        raise AppError(ERR_UNAUTHORIZED, "请先登录", status=401)
    with conn.transaction():
        row = repo.get_by_id(conn, request_id, lock=True)
        if row is None:
            raise AppError(ERR_VALIDATION, "申请不存在", status=404)
        rooms_repo.lock_room(conn, row.room_id)
        _guard_active_member(conn, actor, row.room_id)
        assert_room_role(conn, actor, row.room_id, MANAGER_ROLES)
        if row.requester_id == actor.id:
            raise AppError(ERR_SELF_APPROVAL, "不能批准自己的焦点申请（需另一位管理身份）", status=403)
        if row.status != "pending":
            raise AppError(ERR_VALIDATION, "该申请已处理过", status=409)
        repo.decide(conn, request_id, "approved" if approve else "rejected", actor.id)
        if approve:
            # 同事务设焦点（批准人作为 actor）+ 清掉申请人举手（举手只是申请，拿到焦点就不该再闪）
            focus_service.set_focus(conn, actor, row.room_id, row.requester_id)
            # 004 的 lowered_reason CHECK 只允许 self/other/room_ended：给焦点时用 "other"（他人代放）
            extras_repo.lower_hand(conn, row.room_id, row.requester_id, actor.id, "other")
    return FocusRequestVO(
        id=row.id,
        room_id=row.room_id,
        requester_id=row.requester_id,
        requester_name="",
        status="approved" if approve else "rejected",
        decided_by=actor.id,
        created_at=row.created_at,
        decided_at=None,
    )


def cancel_pending(conn: Connection, room_id: str, user_id: str) -> int:
    """（供焦点清空 / 成员离开时调用）把该人的待批申请置 cancelled。"""
    return repo.cancel_pending_for_user(conn, room_id, user_id)
