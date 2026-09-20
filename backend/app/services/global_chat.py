"""全服大屏聊天（r012）：登录可发、未登录可看；落库是唯一真相，SSE 只做通知。

设计事实源：docs/rounds/r012-superadmin-console/design.md §4.2、ADR-0025。
口径（需求单 §10.1）：Q13=1 全部消息可见、仅当前在线者带在线点；每人窗口内限流；单条 ≤500 字。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from psycopg import Connection

from app.api.errors import ERR_RATE_LIMITED, AppError
from app.config import load_settings
from app.repositories import global_chat as repo
from app.security.ids import new_id
from app.schemas.auth import UserVO
from app.schemas.global_chat import GlobalMessageVO
from app.services import events as events_service
from app.services import presence as presence_service

EVENT_GLOBAL_MESSAGE = "global_message"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _vo(row: repo.GlobalMessageRowWithName, online_ids: set[str]) -> GlobalMessageVO:
    return GlobalMessageVO(
        id=row.message.id,
        user_id=row.message.user_id,
        display_name=row.display_name,
        body=row.message.body,
        author_online=row.message.user_id in online_ids,
        created_at=row.message.created_at,
    )


def list_messages(
    conn: Connection,
    actor: Optional[UserVO],
    *,
    limit: Optional[int] = None,
    before_id: Optional[str] = None,
) -> list[GlobalMessageVO]:
    """最近若干条（**未登录也能看**——大屏是公开面，Q4=1/Q13=1）。

    返回按时间正序（旧的在前），便于前端直接渲染。
    """
    settings = load_settings()
    size = limit if limit is not None else settings.global_chat_page_default
    rows = repo.list_global_messages(conn, size, before_id)
    online_ids = presence_service.online_user_ids(conn)
    return [_vo(row, online_ids) for row in reversed(rows)]


def post_message(conn: Connection, actor: UserVO, body: str) -> GlobalMessageVO:
    """登录用户发言：限流 → 落库（唯一真相）→ 提交后广播通知（SSE）。"""
    settings = load_settings()
    text = body.strip()
    if not text:
        raise AppError("VALIDATION", "不能发送空消息", status=400)

    since = _now() - timedelta(seconds=settings.global_chat_rate_window_seconds)
    recent = repo.count_recent_by_user(conn, actor.id, since)
    if recent >= settings.global_chat_rate_limit:
        raise AppError(
            ERR_RATE_LIMITED,
            f"发得太快了（{settings.global_chat_rate_window_seconds} 秒内最多 "
            f"{settings.global_chat_rate_limit} 条），稍后再试",
            status=429,
        )

    message_id = new_id("gmsg")
    with conn.transaction():
        repo.insert_global_message(conn, repo.NewGlobalMessage(id=message_id, user_id=actor.id, body=text))

    # 提交之后才广播：落库是唯一真相，通知丢了也不影响数据（ADR-0013/0025）
    events_service.publish(EVENT_GLOBAL_MESSAGE, {"id": message_id})

    row = next(
        (
            item
            for item in repo.list_global_messages(conn, 1, None)
            if item.message.id == message_id
        ),
        None,
    )
    if row is None:  # pragma: no cover - 同一连接读自己刚提交的行
        raise AppError("INTERNAL", "发言后无法读取该条消息", status=500)
    return _vo(row, presence_service.online_user_ids(conn))
