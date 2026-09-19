"""限时邀请（r008，作业必做「可生成限时邀请链接或房间码（需设置过期时间）」）。

设计事实源：`docs/rounds/r008-assignment-gaps/design.md` §2.7；决定见 ADR-0019。
口径（用户 2026-09-19）：有效期**最长 1 分钟**（默认 60 秒；上限 `settings.invite_ttl_max_seconds`）；
用码加入 = **直接成为在册成员**（跳过等候室），仍受 8 人上限约束；过期/用尽/非法一律 400 `INVITE_INVALID`。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from psycopg import Connection
from psycopg.errors import UniqueViolation

from app.api.errors import (
    ERR_CONFLICT,
    ERR_INVITE_INVALID,
    ERR_NOT_FOUND,
    ERR_ROOM_ENDED,
    ERR_ROOM_FULL,
    ERR_VALIDATION,
    AppError,
)
from app.config import load_settings
from app.repositories import invites as invites_repo
from app.repositories import rooms as rooms_repo
from app.repositories.invites import InviteRow, NewInvite
from app.schemas.auth import UserVO
from app.schemas.invites import InviteAcceptResult, InviteVO
from app.security.ids import new_code, new_id
from app.services import rooms as rooms_service

CODE_RETRIES = 3


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _vo(row: InviteRow) -> InviteVO:
    return InviteVO(
        id=row.id,
        room_id=row.room_id,
        code=row.code,
        expires_at=row.expires_at,
        max_uses=row.max_uses,
        used_count=row.used_count,
        created_at=row.created_at,
        expired=row.expires_at <= _now(),
    )


def create_invite(
    conn: Connection,
    actor: UserVO,
    room_id: str,
    *,
    ttl_seconds: int = 60,
    max_uses: int = 1,
) -> InviteVO:
    """生成限时邀请码（Host/Moderator；房间必须 `active`）。"""
    settings = load_settings()
    if not (10 <= ttl_seconds <= settings.invite_ttl_max_seconds):
        raise AppError(
            ERR_VALIDATION,
            f"有效期需在 10~{settings.invite_ttl_max_seconds} 秒之间",
            status=400,
        )
    if not (1 <= max_uses <= 50):
        raise AppError(ERR_VALIDATION, "可用次数需在 1~50 之间", status=400)

    with conn.transaction():
        item = rooms_service.assert_room_exists(conn, room_id)
        rooms_service.assert_room_active(item.room)
        rooms_service.assert_manager_role(conn, actor, item.room)
        expires_at = _now() + timedelta(seconds=ttl_seconds)
        last_error: Optional[Exception] = None
        for _ in range(CODE_RETRIES):
            code = new_code().lower()
            try:
                with conn.transaction():  # savepoint：撞码只回滚这一条
                    invites_repo.insert_invite(
                        conn,
                        NewInvite(
                            id=new_id("inv"),
                            room_id=room_id,
                            code=code,
                            created_by=actor.id,
                            expires_at=expires_at,
                            max_uses=max_uses,
                        ),
                    )
                break
            except UniqueViolation as exc:  # 撞码重试
                last_error = exc
        else:
            raise AppError(ERR_CONFLICT, "邀请码生成冲突，请重试", status=409) from last_error

    row = invites_repo.get_invite_by_code(conn, code)
    if row is None:
        raise AppError(ERR_NOT_FOUND, "生成后读不到邀请", status=500)
    return _vo(row)


def list_invites(conn: Connection, actor: UserVO, room_id: str) -> list[InviteVO]:
    """房间的邀请列表（Host/Moderator）；房间可 `ended`，只读。"""
    item = rooms_service.assert_room_exists(conn, room_id)
    rooms_service.assert_manager_role(conn, actor, item.room)
    return [_vo(row) for row in invites_repo.list_invites(conn, room_id)]


def accept_invite(conn: Connection, actor: UserVO, code: str) -> InviteAcceptResult:
    """凭邀请码加入：直接成为在册成员（仍在容量内）。

    幂等：已在册 → `created=False`，不再消耗次数。
    """
    normalized = code.strip()
    if not normalized:
        raise AppError(ERR_INVITE_INVALID, "请填写邀请码", status=400)

    with conn.transaction():
        row = invites_repo.get_invite_by_code(conn, normalized, lock=True)
        if row is None:
            raise AppError(ERR_INVITE_INVALID, "邀请码无效", status=400)

        item = rooms_repo.get_room(conn, row.room_id)
        if item is None:
            raise AppError(ERR_NOT_FOUND, "房间不存在", status=404)
        room = rooms_service.assert_room_active(item.room)

        # 顺序要点（实测踩到）：**已在册的人永远放行**（幂等 200），
        # 不能让「已用完/已过期」把他挡在门外——他只是又点了一次链接。
        if rooms_repo.get_active_member(conn, room.id, actor.id) is not None:
            return InviteAcceptResult(room_id=room.id, created=False, display_name=actor.display_name)

        if row.expires_at <= _now():
            raise AppError(ERR_INVITE_INVALID, "邀请已过期，请让房主重新生成", status=400)
        if row.used_count >= row.max_uses:
            raise AppError(ERR_INVITE_INVALID, "邀请已用完", status=400)

        if rooms_repo.count_active_members(conn, room.id) >= room.capacity:
            raise AppError(ERR_ROOM_FULL, f"房间已满（上限 {room.capacity} 人）", status=409)

        rooms_repo.insert_member(
            conn,
            rooms_repo.NewMember(
                id=new_id("mem"), room_id=room.id, user_id=actor.id, role="participant"
            ),
        )
        invites_repo.bump_invite_used(conn, row.id)
        rooms_service.post_system_message(conn, room.id, actor.id, f"{actor.display_name} 通过邀请链接加入")

    return InviteAcceptResult(room_id=room.id, created=True, display_name=actor.display_name)
