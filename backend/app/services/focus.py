"""焦点发言（r004 / M3）：服务端同步的唯一焦点（ADR-0014 的优先级派生在前端）。

设计事实源：docs/rounds/r004-room-extras/design.md §5.3、§7.1
"""
from __future__ import annotations

from typing import Optional

from psycopg import Connection

from app.api.errors import ERR_UNAUTHORIZED, ERR_VALIDATION, AppError
from app.repositories import room_extras as repo
from app.repositories import rooms as rooms_repo
from app.schemas.auth import UserVO
from app.schemas.rooms import FocusVO
from app.security.ids import new_id
from app.services.messages import _guard_active_member
from app.services.rooms import MANAGER_ROLES, assert_room_role


def _focus_vo(item: Optional[repo.FocusRowWithName]) -> FocusVO:
    if item is None or item.subject_user_id is None:
        return FocusVO()
    return FocusVO(
        subject_user_id=item.subject_user_id,
        subject_name=item.subject_name,
        actor_user_id=item.actor_user_id,
        set_at=item.created_at,
    )


def get_focus(conn: Connection, actor: Optional[UserVO], room_id: str) -> FocusVO:
    """当前焦点（无设置或已取消时为全空对象）。"""
    _guard_active_member(conn, actor, room_id)
    return _focus_vo(repo.latest_focus(conn, room_id))


def set_focus(conn: Connection, actor: Optional[UserVO], room_id: str, subject_user_id: Optional[str]) -> FocusVO:
    """房主/协管指定或取消焦点（`subject_user_id=None` = 取消）。"""
    if actor is None:
        raise AppError(ERR_UNAUTHORIZED, "请先登录", status=401)
    with conn.transaction():
        rooms_repo.lock_room(conn, room_id)
        _guard_active_member(conn, actor, room_id)
        assert_room_role(conn, actor, room_id, MANAGER_ROLES)
        if subject_user_id is not None and rooms_repo.get_active_member(conn, room_id, subject_user_id) is None:
            raise AppError(ERR_VALIDATION, "焦点对象不在房间中", status=400)
        repo.insert_focus(conn, new_id("focus"), room_id, subject_user_id, actor.id)
        item = repo.latest_focus(conn, room_id)
    return _focus_vo(item)


def grant_focus_from_hand(conn: Connection, actor: Optional[UserVO], room_id: str, subject_user_id: str) -> FocusVO:
    """管理在**举手者**格上点「给焦点」：设焦点 + 清掉他的举手（一条事务，r009 / ADR-0021 D2）。

    与 `set_focus` 的区别：这里语义是「回应举手」，所以必须真的把举手放下（否则格子会一直闪）。
    """
    if actor is None:
        raise AppError(ERR_UNAUTHORIZED, "请先登录", status=401)
    with conn.transaction():
        rooms_repo.lock_room(conn, room_id)
        _guard_active_member(conn, actor, room_id)
        assert_room_role(conn, actor, room_id, MANAGER_ROLES)
        if rooms_repo.get_active_member(conn, room_id, subject_user_id) is None:
            raise AppError(ERR_VALIDATION, "对方不在房间中", status=400)
        repo.insert_focus(conn, new_id("focus"), room_id, subject_user_id, actor.id)
        # 004 的 lowered_reason CHECK 只允许 self/other/room_ended
        repo.lower_hand(conn, room_id, subject_user_id, actor.id, "other")
        item = repo.latest_focus(conn, room_id)
    return _focus_vo(item)
