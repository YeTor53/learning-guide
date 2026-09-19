"""房内扩展能力接口（群聊 / 举手 / 焦点；路由薄壳：取依赖 → 调 service → 信封）。

设计事实源：docs/rounds/r004-room-extras/design.md §4（8 条路由）
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from psycopg import Connection

from app.api.deps import current_user, current_user_optional, db_conn
from app.api.envelope import ok
from app.schemas.auth import UserVO
from app.schemas.rooms import FocusIn, MessageIn
from app.services import focus as focus_service
from app.services import hands as hands_service
from app.services import messages as messages_service

router = APIRouter(tags=["room-extras"])


def _dump(model) -> dict:
    """VO → JSON 字典（camelCase，时间转 ISO 串）。"""
    return model.model_dump(mode="json", by_alias=True)


def _dump_all(models) -> list[dict]:
    return [_dump(item) for item in models]


# ---------------- 群聊 ----------------

@router.post("/rooms/{room_id}/messages", status_code=201)
def post_message(
    room_id: str,
    payload: MessageIn,
    actor: UserVO = Depends(current_user),
    conn: Connection = Depends(db_conn),
):
    """发消息（落库为唯一真相；房内实时广播由前端在 HTTP 成功后发出，ADR-0013）。"""
    return ok({"message": _dump(messages_service.post_message(conn, actor, room_id, payload.body))}, status=201)


@router.get("/rooms/{room_id}/messages", status_code=200)
def list_messages(
    room_id: str,
    before: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    actor: Optional[UserVO] = Depends(current_user_optional),
    conn: Connection = Depends(db_conn),
):
    """按房间取最近消息（时间正序）；`before` 传上一页最早一条的 id。"""
    items = messages_service.list_messages(conn, actor, room_id, before, limit)
    return ok({"messages": _dump_all(items)}, status=200)


# ---------------- 举手 ----------------

@router.get("/rooms/{room_id}/hand-raises", status_code=200)
def list_hands(
    room_id: str,
    actor: Optional[UserVO] = Depends(current_user_optional),
    conn: Connection = Depends(db_conn),
):
    """当前举手快照（按举手时间升序）。"""
    return ok({"hands": _dump_all(hands_service.list_hands(conn, actor, room_id))}, status=200)


@router.post("/rooms/{room_id}/hand-raise", status_code=200)
def raise_hand(
    room_id: str,
    actor: UserVO = Depends(current_user),
    conn: Connection = Depends(db_conn),
):
    """举手（幂等）。"""
    return ok({"hands": _dump_all(hands_service.raise_hand(conn, actor, room_id))}, status=200)


@router.delete("/rooms/{room_id}/hand-raise", status_code=200)
def lower_own_hand(
    room_id: str,
    actor: UserVO = Depends(current_user),
    conn: Connection = Depends(db_conn),
):
    """自己放下手（幂等）。"""
    return ok({"hands": _dump_all(hands_service.lower_own_hand(conn, actor, room_id))}, status=200)


@router.delete("/rooms/{room_id}/hand-raise/{user_id}", status_code=200)
def lower_other_hand(
    room_id: str,
    user_id: str,
    actor: UserVO = Depends(current_user),
    conn: Connection = Depends(db_conn),
):
    """房主/协管放下他人的举手。"""
    return ok({"hands": _dump_all(hands_service.lower_other_hand(conn, actor, room_id, user_id))}, status=200)


# ---------------- 焦点 ----------------

@router.get("/rooms/{room_id}/focus", status_code=200)
def get_focus(
    room_id: str,
    actor: Optional[UserVO] = Depends(current_user_optional),
    conn: Connection = Depends(db_conn),
):
    """当前焦点（无焦点时字段全空）。"""
    return ok({"focus": _dump(focus_service.get_focus(conn, actor, room_id))}, status=200)


@router.post("/rooms/{room_id}/focus", status_code=200)
def set_focus(
    room_id: str,
    payload: FocusIn,
    actor: UserVO = Depends(current_user),
    conn: Connection = Depends(db_conn),
):
    """房主/协管指定或取消焦点（`userId: null` 表示取消）。"""
    return ok({"focus": _dump(focus_service.set_focus(conn, actor, room_id, payload.user_id))}, status=200)
