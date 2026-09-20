"""在线口径（r012）：前端定时上报的心跳时间。

设计事实源：docs/rounds/r012-superadmin-console/design.md §2.6（Q14=2：前端短轮询，不用「请求即心跳」）。
- 写入点只有一处：`POST /api/presence` → `touch()`（每次都写，周期由前端控制，默认 60 秒）；
- 判据窗口 `PRESENCE_ONLINE_SECONDS`（默认 120 = 2× 周期，容一次丢包不掉线；单点可调）；
- 只碰 `users.last_seen_at` 一列，不涉及房间/成员逻辑。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from psycopg import Connection

from app.config import load_settings
from app.repositories import users as users_repo


def _now() -> datetime:
    return datetime.now(timezone.utc)


def touch(conn: Connection, user_id: str, *, now: Optional[datetime] = None) -> datetime:
    """把该用户的 `last_seen_at` 写成当前时间并返回它（幂等，无内存态）。"""
    at = now or _now()
    users_repo.touch_last_seen(conn, user_id, at)
    return at


def is_online(
    last_seen_at: Optional[datetime],
    *,
    now: Optional[datetime] = None,
    window_seconds: Optional[int] = None,
) -> bool:
    """在线 = `now - last_seen_at ≤ window_seconds`；无心跳记录（NULL）一律离线。"""
    if last_seen_at is None:
        return False
    window = window_seconds if window_seconds is not None else load_settings().presence_online_seconds
    return (now or _now()) - last_seen_at <= timedelta(seconds=window)


def online_user_ids(conn: Connection, *, now: Optional[datetime] = None) -> set[str]:
    """当前在线用户 id 集合（大屏面板的「在线」判据；一次 SQL 取回）。"""
    window = load_settings().presence_online_seconds
    since = (now or _now()) - timedelta(seconds=window)
    return users_repo.list_online_user_ids(conn, since)
