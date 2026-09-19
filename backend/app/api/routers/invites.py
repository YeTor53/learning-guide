"""邀请接口（r008；路由薄壳）。

设计事实源：`docs/rounds/r008-assignment-gaps/design.md` §2.8
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from psycopg import Connection

from app.api.deps import current_user, db_conn
from app.api.envelope import ok
from app.schemas.auth import UserVO
from app.schemas.invites import InviteCreateIn
from app.services import invites as invites_service

router = APIRouter(tags=["invites"])


def _dump(model) -> dict:
    return model.model_dump(mode="json", by_alias=True)


@router.post("/rooms/{room_id}/invites", status_code=201)
def create_invite(
    room_id: str,
    payload: InviteCreateIn,
    actor: UserVO = Depends(current_user),
    conn: Connection = Depends(db_conn),
):
    """生成限时邀请码（Host/Moderator；默认 60 秒有效、1 次可用）。"""
    item = invites_service.create_invite(
        conn, actor, room_id, ttl_seconds=payload.ttl_seconds, max_uses=payload.max_uses
    )
    return ok(_dump(item), status=201)


@router.get("/rooms/{room_id}/invites", status_code=200)
def list_invites(
    room_id: str,
    actor: UserVO = Depends(current_user),
    conn: Connection = Depends(db_conn),
):
    """房间的邀请列表（Host/Moderator）。"""
    items = invites_service.list_invites(conn, actor, room_id)
    return ok({"invites": [_dump(item) for item in items]}, status=200)


@router.post("/invites/{code}/accept", status_code=201)
def accept_invite(
    code: str,
    actor: UserVO = Depends(current_user),
    conn: Connection = Depends(db_conn),
):
    """凭邀请码加入（直接成为在册成员）；已在册时幂等返回 200。"""
    result = invites_service.accept_invite(conn, actor, code)
    return ok(_dump(result), status=201 if result.created else 200)
