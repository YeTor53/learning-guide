"""管理后台业务（r012）：鉴权 → 查询/动作 → 审计。

设计事实源：docs/rounds/r012-superadmin-console/design.md §3.2（Q5=1 三列表 + 三动作；Q6=1 复用房主端点；Q7=1 审计）。
规则：
- 每个函数**第一行**就 `roles.assert_superadmin(actor)`（服务端强制，前端可见性不是边界）；
- 写动作的审计与业务动作**同一个事务**（有动作必有流水）；
- 结束 / 重生纪要**复用既有 service**（`assert_room_role` / `assert_manager_role` 已对超管放行）；
- 触达 LiveKit 的调用一律在事务提交之后（ADR-0011 条 4）。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from psycopg import Connection

from app.api.errors import ERR_NOT_FOUND, AppError
from app.repositories import admin as repo
from app.repositories import rooms as rooms_repo
from app.schemas.admin import (
    AdminAuditItem,
    AdminRoomItem,
    AdminSummaryItem,
    AdminUserItem,
)
from app.schemas.auth import UserVO
from app.schemas.summary import SessionSummaryVO
from app.schemas.rooms import RoomVO
from app.security.ids import new_id
from app.services import livekit as livekit_service
from app.services import rooms as rooms_service
from app.services import roles as roles_service
from app.services import summary as summary_service

def _now() -> datetime:
    return datetime.now(timezone.utc)


# 审计 action 词表（单点；新增管理动作必须在此登记）
ADMIN_ACTION_ROOM_END = "room.end"
ADMIN_ACTION_ROOM_DELETE = "room.delete"
ADMIN_ACTION_SUMMARY_REGENERATE = "room.summary_regenerate"
ADMIN_ACTIONS = (ADMIN_ACTION_ROOM_END, ADMIN_ACTION_ROOM_DELETE, ADMIN_ACTION_SUMMARY_REGENERATE)


def _audit(
    conn: Connection,
    actor: UserVO,
    action: str,
    target_type: str,
    target_id: str,
    detail: Optional[dict] = None,
) -> None:
    """统一写审计（与调用方同一个事务）。"""
    repo.insert_audit(
        conn,
        repo.NewAudit(
            id=new_id("audit"),
            actor_id=actor.id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=detail or {},
            created_at=_now(),
        ),
    )


def _room_item(row: repo.AdminRoomRow) -> AdminRoomItem:
    return AdminRoomItem(**row.__dict__)


def _user_item(row: repo.AdminUserRow) -> AdminUserItem:
    return AdminUserItem(**row.__dict__)


def _summary_item(row: repo.AdminSummaryRow) -> AdminSummaryItem:
    return AdminSummaryItem(**row.__dict__)


def _audit_item(row: repo.AdminAuditRow) -> AdminAuditItem:
    return AdminAuditItem(**row.__dict__)


def list_rooms(conn: Connection, actor: Optional[UserVO], f: repo.AdminRoomFilter) -> tuple[list[AdminRoomItem], int]:
    roles_service.assert_superadmin(actor)
    items, total = repo.list_rooms_page(conn, f)
    return [_room_item(row) for row in items], total


def list_users(conn: Connection, actor: Optional[UserVO], f: repo.AdminUserFilter) -> tuple[list[AdminUserItem], int]:
    roles_service.assert_superadmin(actor)
    items, total = repo.list_users_page(conn, f)
    return [_user_item(row) for row in items], total


def list_summaries(
    conn: Connection, actor: Optional[UserVO], f: repo.AdminSummaryFilter
) -> tuple[list[AdminSummaryItem], int]:
    roles_service.assert_superadmin(actor)
    items, total = repo.list_summaries_page(conn, f)
    return [_summary_item(row) for row in items], total


def list_audit(
    conn: Connection, actor: Optional[UserVO], f: repo.AdminAuditFilter
) -> tuple[list[AdminAuditItem], int]:
    roles_service.assert_superadmin(actor)
    items, total = repo.list_audit_page(conn, f)
    return [_audit_item(row) for row in items], total


def end_room(conn: Connection, actor: Optional[UserVO], room_id: str) -> RoomVO:
    """超管结束任意房间：复用 `rooms_service.end_room`（旁路已放行），事务内补一条审计。"""
    roles_service.assert_superadmin(actor)
    item = rooms_repo.get_room(conn, room_id)
    if item is None:
        raise AppError(ERR_NOT_FOUND, "房间不存在", status=404)
    with conn.transaction():
        _audit(
            conn,
            actor,
            ADMIN_ACTION_ROOM_END,
            "room",
            room_id,
            {"title": item.room.title, "hostId": item.room.host_id, "before": {"status": item.room.status}},
        )
    return rooms_service.end_room(conn, actor, room_id)


def delete_room(conn: Connection, actor: Optional[UserVO], room_id: str) -> dict:
    """超管硬删房间：快照 → 审计 → 删行（级联）→ 提交后删 LiveKit 房间。"""
    roles_service.assert_superadmin(actor)
    snapshot = repo.get_room_snapshot(conn, room_id)
    if snapshot is None:
        raise AppError(ERR_NOT_FOUND, "房间不存在", status=404)
    with conn.transaction():
        _audit(conn, actor, ADMIN_ACTION_ROOM_DELETE, "room", room_id, {"snapshot": snapshot})
        deleted = repo.delete_room(conn, room_id)
        if deleted != 1:
            raise AppError(ERR_NOT_FOUND, "房间不存在", status=404)
    livekit_applied = rooms_service._safe_livekit(lambda: livekit_service.delete_room(room_id))
    return {"deleted": True, "livekitApplied": livekit_applied}


def regenerate_summary(conn: Connection, actor: Optional[UserVO], room_id: str) -> SessionSummaryVO:
    """超管生成/重生纪要：复用 `summary_service.generate_summary`（其 `assert_manager_role` 已放行）。"""
    roles_service.assert_superadmin(actor)
    summary = summary_service.generate_summary(conn, actor, room_id)
    with conn.transaction():
        _audit(
            conn,
            actor,
            ADMIN_ACTION_SUMMARY_REGENERATE,
            "summary",
            room_id,
            {"summaryId": summary.id, "status": summary.status, "model": summary.model},
        )
    return summary
