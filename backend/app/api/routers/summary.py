"""纪要接口（r008；路由薄壳：取依赖 → 调 service → 信封）。

设计事实源：`docs/rounds/r008-assignment-gaps/design.md` §2.8
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from psycopg import Connection

from app.api.deps import current_user, db_conn
from app.api.envelope import ok
from app.schemas.auth import UserVO
from app.services import summary as summary_service

router = APIRouter(tags=["summary"])


def _dump(model) -> dict:
    """VO → JSON 字典（camelCase，时间转 ISO 串）。"""
    return model.model_dump(mode="json", by_alias=True)


@router.post("/rooms/{room_id}/summary", status_code=201)
def create_summary(
    room_id: str,
    actor: UserVO = Depends(current_user),
    conn: Connection = Depends(db_conn),
):
    """生成/重新生成讨论纪要（Host/Moderator）。"""
    return ok(_dump(summary_service.generate_summary(conn, actor, room_id)), status=201)


@router.get("/rooms/{room_id}/summary", status_code=200)
def read_summary(
    room_id: str,
    actor: UserVO = Depends(current_user),
    conn: Connection = Depends(db_conn),
):
    """查看讨论纪要；未生成时 `data.summary = null`。"""
    item = summary_service.get_summary(conn, actor, room_id)
    return ok({"summary": _dump(item) if item is not None else None}, status=200)
