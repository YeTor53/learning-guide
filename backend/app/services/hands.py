"""举手（r004 / M3）：状态落库 + 快照返回（前端广播全量快照，ADR-0013）。

设计事实源：docs/rounds/r004-room-extras/design.md §5.2、§4
实现细节：设计里的第 5 个函数 `clear_hands_for_room_end` 折进 `services/rooms.end_room`
（直接调 `repositories/room_extras.lower_all_hands`），避免 `rooms ↔ hands` 的 service 层循环 import。
"""
from __future__ import annotations

from typing import Optional

from psycopg import Connection

from app.api.errors import ERR_UNAUTHORIZED, ERR_VALIDATION, AppError
from app.repositories import room_extras as repo
from app.repositories import rooms as rooms_repo
from app.schemas.auth import UserVO
from app.schemas.rooms import HandVO
from app.security.ids import new_id
from app.services.messages import _guard_active_member
from app.services.rooms import MANAGER_ROLES, assert_room_role


def _hand_vo(item: repo.HandRowWithName) -> HandVO:
    return HandVO(id=item.id, user_id=item.user_id, display_name=item.display_name, raised_at=item.raised_at)


def list_hands(conn: Connection, actor: Optional[UserVO], room_id: str) -> list[HandVO]:
    """当前举手快照（按举手时间升序）。"""
    _guard_active_member(conn, actor, room_id)
    return [_hand_vo(item) for item in repo.list_active_hands(conn, room_id)]


def raise_hand(conn: Connection, actor: Optional[UserVO], room_id: str) -> list[HandVO]:
    """举手（幂等：已在举则原样返回快照）。"""
    with conn.transaction():
        rooms_repo.lock_room(conn, room_id)
        _guard_active_member(conn, actor, room_id)
        repo.insert_hand(conn, new_id("hand"), room_id, actor.id)
    return [_hand_vo(item) for item in repo.list_active_hands(conn, room_id)]


def lower_own_hand(conn: Connection, actor: Optional[UserVO], room_id: str) -> list[HandVO]:
    """自己放下手（幂等：没有活跃举手也不报错）。"""
    with conn.transaction():
        rooms_repo.lock_room(conn, room_id)
        _guard_active_member(conn, actor, room_id)
        repo.lower_hand(conn, room_id, actor.id, by=actor.id, reason="self")
    return [_hand_vo(item) for item in repo.list_active_hands(conn, room_id)]


def lower_other_hand(conn: Connection, actor: Optional[UserVO], room_id: str, target_user_id: str) -> list[HandVO]:
    """房主/协管放下他人的举手（记录 `lowered_by`）。"""
    if actor is None:
        raise AppError(ERR_UNAUTHORIZED, "请先登录", status=401)
    with conn.transaction():
        rooms_repo.lock_room(conn, room_id)
        _guard_active_member(conn, actor, room_id)
        assert_room_role(conn, actor, room_id, MANAGER_ROLES)
        changed = repo.lower_hand(conn, room_id, target_user_id, by=actor.id, reason="other")
        if not changed:
            raise AppError(ERR_VALIDATION, "该成员没有正在举手", status=400)
    return [_hand_vo(item) for item in repo.list_active_hands(conn, room_id)]
