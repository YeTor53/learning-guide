"""全服大屏聊天接口（r012）。

设计事实源：docs/rounds/r012-superadmin-console/design.md §4.4（`GET` 未登录可读、`POST` 需登录）。
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from psycopg import Connection

from app.api.deps import current_user, current_user_optional, db_conn
from app.api.envelope import ok
from app.schemas.auth import UserVO
from app.schemas.global_chat import GlobalMessageIn
from app.services import global_chat as global_chat_service

router = APIRouter(tags=["global-chat"])


def _dump(model) -> dict:
    return model.model_dump(mode="json", by_alias=True)


@router.get("/global-messages", status_code=200)
def list_global_messages(
    limit: Optional[int] = Query(default=None, ge=1, le=100),
    before_id: Optional[str] = Query(default=None, max_length=64),
    actor: Optional[UserVO] = Depends(current_user_optional),
    conn: Connection = Depends(db_conn),
):
    """大屏消息列表（未登录也可读）；按时间正序返回。"""
    items = global_chat_service.list_messages(conn, actor, limit=limit, before_id=before_id)
    return ok({"items": [_dump(item) for item in items]}, status=200)


@router.post("/global-messages", status_code=201)
def post_global_message(
    payload: GlobalMessageIn,
    actor: UserVO = Depends(current_user),
    conn: Connection = Depends(db_conn),
):
    """发言（需登录）；超限 → 429 `RATE_LIMITED`。"""
    return ok(_dump(global_chat_service.post_message(conn, actor, payload.body)), status=201)
