"""在线心跳接口（r012）。

设计事实源：docs/rounds/r012-superadmin-console/design.md §2.6（Q14=2 短轮询口径）。
路由表：POST /api/presence —— 登录必需、无请求体；每次调用写 `users.last_seen_at` 并回传新值。
前端调用点：`frontend/src/hooks/usePresenceBeat.ts`（默认 60 秒一次，仅页面可见且已登录时）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from psycopg import Connection

from app.api.deps import current_user, db_conn
from app.api.envelope import ok
from app.schemas.auth import UserVO
from app.services import presence as presence_service

router = APIRouter(prefix="/presence", tags=["presence"])


@router.post("", status_code=200)
def beat(user: UserVO = Depends(current_user), conn: Connection = Depends(db_conn)):
    """上报一次心跳；返回 `{ok, lastSeenAt}`（前端不依赖返回值，只作观测）。"""
    at = presence_service.touch(conn, user.id)
    return ok({"ok": True, "lastSeenAt": at.isoformat()}, status=200)
