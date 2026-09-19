"""群聊消息（r004 / M3）：落库为唯一真相，房内广播由前端负责（ADR-0013）。

设计事实源：docs/rounds/r004-room-extras/design.md §5.1、§4
"""
from __future__ import annotations

from typing import Optional

from psycopg import Connection

from app.api.errors import ERR_FORBIDDEN, ERR_NOT_FOUND, ERR_ROOM_ENDED, ERR_UNAUTHORIZED, ERR_VALIDATION, AppError
from app.repositories import room_extras as repo
from app.repositories import rooms as rooms_repo
from app.schemas.auth import UserVO
from app.schemas.rooms import MessageVO
from app.security.ids import new_id
from app.services.rooms import assert_room_active

MESSAGE_LIMIT_MAX = 100
MESSAGE_LIMIT_DEFAULT = 50


def _message_vo(item: repo.MessageRowWithName) -> MessageVO:
    (mid, _room_id, user_id, body, kind, created_at) = item.message
    return MessageVO(id=mid, user_id=user_id, display_name=item.display_name, body=body, kind=kind, created_at=created_at)


def _guard_active_member(conn: Connection, actor: Optional[UserVO], room_id: str) -> None:
    """统一前置：未登录 401 → 房间不存在 404 → 已结束 409 → 非活跃成员 403。"""
    if actor is None:
        raise AppError(ERR_UNAUTHORIZED, "请先登录", status=401)
    room = rooms_repo.get_room(conn, room_id)
    if room is None:
        raise AppError(ERR_NOT_FOUND, "房间不存在", status=404)
    assert_room_active(room.room)
    if rooms_repo.get_active_member(conn, room_id, actor.id) is None:
        raise AppError(ERR_FORBIDDEN, "你不在该房间中（或已被移出）", status=403)


def list_messages(
    conn: Connection, actor: Optional[UserVO], room_id: str, before: Optional[str], limit: int = MESSAGE_LIMIT_DEFAULT
) -> list[MessageVO]:
    """按房间取最近消息（时间正序返回，前端直接渲染）；`before` 是上一页最早一条的 id。"""
    _guard_active_member(conn, actor, room_id)
    if limit < 1 or limit > MESSAGE_LIMIT_MAX:
        raise AppError(ERR_VALIDATION, f"limit 需在 1~{MESSAGE_LIMIT_MAX} 之间", status=400)
    cursor = None
    if before:
        cursor = repo.get_message_time(conn, room_id, before)
        if cursor is None:
            raise AppError(ERR_VALIDATION, "分页游标不属于该房间", status=400)
    rows = repo.list_messages(conn, room_id, cursor, limit)
    return [_message_vo(item) for item in reversed(rows)]


def post_message(conn: Connection, actor: Optional[UserVO], room_id: str, body: str) -> MessageVO:
    """发消息：锁房间行（防「刚结束仍写入」竞态）→ 校验 → 落库 → 返回带显示名的 VO。"""
    with conn.transaction():
        rooms_repo.lock_room(conn, room_id)
        _guard_active_member(conn, actor, room_id)
        text = (body or "").strip()
        if not text:
            raise AppError(ERR_VALIDATION, "消息不能为空", status=400)
        message_id = new_id("msg")
        repo.insert_message(conn, repo.NewMessage(id=message_id, room_id=room_id, user_id=actor.id, body=text))
        created_at = repo.get_message_time(conn, room_id, message_id)
    return MessageVO(
        id=message_id,
        user_id=actor.id,
        display_name=actor.display_name,
        body=text,
        kind="chat",
        created_at=created_at,
    )
