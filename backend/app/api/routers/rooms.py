"""房间接口（路由薄壳：取依赖 → 调 service → 信封）。

设计事实源：docs/02-modules/r001-rooms.md §5（接口清单，9 条路由）、§6.7
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from psycopg import Connection

from app.api.deps import current_user, current_user_optional, db_conn
from app.api.envelope import ok
from app.api.errors import ERR_UNAUTHORIZED, AppError
from app.repositories.rooms import RoomFilter
from app.schemas.auth import UserVO
from app.schemas.rooms import CreateRoomIn, JoinRequestIn, TOPICS
from app.services import rooms as rooms_service

router = APIRouter(tags=["rooms"])

LIMIT_MAX = 100


def _dump(model) -> dict:
    """VO → JSON 字典（camelCase，时间转 ISO 串）。"""
    return model.model_dump(mode="json", by_alias=True)


@router.get("/rooms", status_code=200)
def list_rooms(
    status: str = Query(default="active", pattern="^(active|ended|all)$"),
    topic: Optional[str] = Query(default=None),
    mine: int = Query(default=0, ge=0, le=1),
    limit: int = Query(default=20, ge=1, le=LIMIT_MAX),
    offset: int = Query(default=0, ge=0),
    actor: Optional[UserVO] = Depends(current_user_optional),
    conn: Connection = Depends(db_conn),
):
    """房间列表；访客可浏览，`mine=1` 只看我参与/我建过的房间（需登录）。"""
    if topic is not None and topic not in TOPICS:
        raise AppError("VALIDATION", f"未知主题：{topic}", status=400)
    if mine == 1 and actor is None:
        raise AppError(ERR_UNAUTHORIZED, "请先登录", status=401)
    filters = RoomFilter(
        status=None if status == "all" else status,
        topic=topic,
        mine_user_id=actor.id if (mine == 1 and actor) else None,
        limit=limit,
        offset=offset,
    )
    items, total = rooms_service.list_rooms(conn, actor, filters)
    return ok({"rooms": [_dump(item) for item in items], "total": total, "limit": limit, "offset": offset})


@router.post("/rooms", status_code=201)
def create_room(payload: CreateRoomIn, actor: UserVO = Depends(current_user), conn: Connection = Depends(db_conn)):
    """建房；创建者自动成为该房间 Host。"""
    return ok(_dump(rooms_service.create_room(conn, actor, payload)), status=201)


@router.get("/rooms/{room_id}", status_code=200)
def get_room(room_id: str, actor: Optional[UserVO] = Depends(current_user_optional), conn: Connection = Depends(db_conn)):
    """房间详情：信息 + 成员 + 最近 20 条消息 + 我的状态。"""
    return ok(_dump(rooms_service.get_room_detail(conn, actor, room_id)), status=200)


@router.post("/rooms/{room_id}/join-requests", status_code=201)
def create_join_request(
    room_id: str,
    payload: JoinRequestIn,
    actor: UserVO = Depends(current_user),
    conn: Connection = Depends(db_conn),
):
    """提交加入申请（等候室入口）。"""
    return ok(_dump(rooms_service.request_join(conn, actor, room_id, payload.message)), status=201)


@router.get("/rooms/{room_id}/join-requests", status_code=200)
def list_join_requests(
    room_id: str,
    status: Optional[str] = Query(default=None, pattern="^(pending|approved|rejected|withdrawn|cancelled)$"),
    actor: UserVO = Depends(current_user),
    conn: Connection = Depends(db_conn),
):
    """申请列表（Host/Moderator 可见；房间结束后仍可追溯查看）。"""
    items = rooms_service.list_join_requests(conn, actor, room_id, status)
    return ok({"requests": [_dump(item) for item in items]}, status=200)


@router.post("/join-requests/{request_id}/withdraw", status_code=200)
def withdraw_join_request(request_id: str, actor: UserVO = Depends(current_user), conn: Connection = Depends(db_conn)):
    """撤回自己的待批申请（撤回后可再次申请）。"""
    result = rooms_service.withdraw_join_request(conn, actor, request_id)
    return ok({"request": _dump(result)}, status=200)


@router.post("/join-requests/{request_id}/approve", status_code=200)
def approve_join_request(request_id: str, actor: UserVO = Depends(current_user), conn: Connection = Depends(db_conn)):
    """批准加入：成功返回 {request, member}。"""
    result = rooms_service.approve_join_request(conn, actor, request_id)
    return ok({"request": _dump(result.request), "member": _dump(result.member)}, status=200)


@router.post("/join-requests/{request_id}/reject", status_code=200)
def reject_join_request(request_id: str, actor: UserVO = Depends(current_user), conn: Connection = Depends(db_conn)):
    """拒绝加入：成功返回 {request}。"""
    result = rooms_service.reject_join_request(conn, actor, request_id)
    return ok({"request": _dump(result)}, status=200)


@router.post("/rooms/{room_id}/leave", status_code=200)
def leave_room(room_id: str, actor: UserVO = Depends(current_user), conn: Connection = Depends(db_conn)):
    """离开房间（房主不可直接离开）。"""
    rooms_service.leave_room(conn, actor, room_id)
    return ok({}, status=200)


@router.post("/rooms/{room_id}/end", status_code=200)
def end_room(room_id: str, actor: UserVO = Depends(current_user), conn: Connection = Depends(db_conn)):
    """结束房间：房间置 ended + 活跃成员转 inactive/room_ended + 待批申请转 cancelled（同事务）。"""
    return ok(_dump(rooms_service.end_room(conn, actor, room_id)), status=200)
