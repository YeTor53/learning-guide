"""管理后台接口（r012）：三列表 + 三动作（+ 审计流水）。

设计事实源：docs/rounds/r012-superadmin-console/design.md §3.3。
鉴权：每个端点都依赖 `current_superadmin`（未登录 401 / 非超管 403），**不靠前端隐藏入口**。
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from psycopg import Connection

from app.api.deps import current_superadmin, db_conn
from app.api.envelope import ok
from app.repositories.admin import AdminAuditFilter, AdminRoomFilter, AdminSummaryFilter, AdminUserFilter
from app.schemas.auth import UserVO
from app.services import admin as admin_service
from app.services import presence as presence_service

router = APIRouter(prefix="/admin", tags=["admin"])

LIMIT_MAX = 100


def _dump(model) -> dict:
    return model.model_dump(mode="json", by_alias=True)


@router.get("/rooms", status_code=200)
def list_rooms(
    status: Optional[str] = Query(default=None, pattern="^(active|ended)$"),
    q: Optional[str] = Query(default=None, max_length=64),
    limit: int = Query(default=20, ge=1, le=LIMIT_MAX),
    offset: int = Query(default=0, ge=0),
    actor: UserVO = Depends(current_superadmin),
    conn: Connection = Depends(db_conn),
):
    """房间列表（含房主名 / 在册人数 / 待批数 / 纪要状态）。"""
    items, total = admin_service.list_rooms(
        conn, actor, AdminRoomFilter(status=status, q=q, limit=limit, offset=offset)
    )
    return ok({"items": [_dump(item) for item in items], "total": total, "limit": limit, "offset": offset})


@router.get("/users", status_code=200)
def list_users(
    q: Optional[str] = Query(default=None, max_length=64),
    online_only: int = Query(default=0, ge=0, le=1),
    limit: int = Query(default=20, ge=1, le=LIMIT_MAX),
    offset: int = Query(default=0, ge=0),
    actor: UserVO = Depends(current_superadmin),
    conn: Connection = Depends(db_conn),
):
    """用户列表（含最后心跳 / 参与房间数 / 发言数）。`onlineOnly=1` 只看当前在线。"""
    since = presence_service.online_since() if online_only == 1 else None
    items, total = admin_service.list_users(
        conn, actor, AdminUserFilter(q=q, online_since=since, limit=limit, offset=offset)
    )
    return ok({"items": [_dump(item) for item in items], "total": total, "limit": limit, "offset": offset})


@router.get("/summaries", status_code=200)
def list_summaries(
    status: Optional[str] = Query(default=None, pattern="^(ready|failed|pending)$"),
    limit: int = Query(default=20, ge=1, le=LIMIT_MAX),
    offset: int = Query(default=0, ge=0),
    actor: UserVO = Depends(current_superadmin),
    conn: Connection = Depends(db_conn),
):
    """纪要列表（含房间标题 / 状态 / 模型 / 字数）。"""
    items, total = admin_service.list_summaries(
        conn, actor, AdminSummaryFilter(status=status, limit=limit, offset=offset)
    )
    return ok({"items": [_dump(item) for item in items], "total": total, "limit": limit, "offset": offset})


@router.get("/audit", status_code=200)
def list_audit(
    action: Optional[str] = Query(default=None, max_length=64),
    limit: int = Query(default=20, ge=1, le=LIMIT_MAX),
    offset: int = Query(default=0, ge=0),
    actor: UserVO = Depends(current_superadmin),
    conn: Connection = Depends(db_conn),
):
    """管理动作流水（每条动作一行；删房后 targetId 允许悬空，快照在 detail 里）。"""
    items, total = admin_service.list_audit(
        conn, actor, AdminAuditFilter(action=action, limit=limit, offset=offset)
    )
    return ok({"items": [_dump(item) for item in items], "total": total, "limit": limit, "offset": offset})


@router.post("/rooms/{room_id}/end", status_code=200)
def end_room(room_id: str, actor: UserVO = Depends(current_superadmin), conn: Connection = Depends(db_conn)):
    """结束任意房间（与房主「结束房间」同结果 + 一条审计）。"""
    return ok(_dump(admin_service.end_room(conn, actor, room_id)), status=200)


@router.delete("/rooms/{room_id}", status_code=200)
def delete_room(room_id: str, actor: UserVO = Depends(current_superadmin), conn: Connection = Depends(db_conn)):
    """硬删房间（不可逆）：本库行级联删 + LiveKit 房间一并删；审计流水保留。"""
    return ok(admin_service.delete_room(conn, actor, room_id), status=200)


@router.post("/rooms/{room_id}/summary", status_code=201)
def regenerate_summary(room_id: str, actor: UserVO = Depends(current_superadmin), conn: Connection = Depends(db_conn)):
    """生成/重生该房讨论纪要（复用纪要服务；未配置密钥 503 / 失败 502 语义不变）。"""
    return ok(_dump(admin_service.regenerate_summary(conn, actor, room_id)), status=201)
