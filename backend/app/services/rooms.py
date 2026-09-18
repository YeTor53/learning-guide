"""房间业务规则（唯一写库入口；事务边界与行锁都在本层）。

设计事实源：docs/02-modules/r001-rooms.md §4（规则表）、§6.4（函数签名）、§8（并发与边界）
并发核心：`lock_room`（`SELECT ... FOR UPDATE`）是批准 / 拒绝 / 离开 / 结束共用的**唯一锁点**；
          重复申请由部分唯一索引 `ux_join_requests_pending` 兜底并映射为 `ALREADY_PENDING`。
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional, Sequence

from psycopg import Connection
from psycopg.errors import UniqueViolation

from app.api.errors import (
    ERR_ALREADY_MEMBER,
    ERR_ALREADY_PENDING,
    ERR_CONFLICT,
    ERR_FORBIDDEN,
    ERR_HOST_CANNOT_LEAVE,
    ERR_INTERNAL,
    ERR_NOT_FOUND,
    ERR_NOT_MEMBER,
    ERR_ROOM_ENDED,
    ERR_ROOM_FULL,
    ERR_UNAUTHORIZED,
    ERR_VALIDATION,
    AppError,
)
from app.config import load_settings
from app.repositories import rooms as repo
from app.repositories.rooms import MemberRow, RoomRow, RoomWithHost
from app.repositories.users import get_user_by_id
from app.schemas.auth import UserVO
from app.schemas.rooms import (
    ApprovalResult,
    CreateRoomIn,
    JoinRequestVO,
    KickResult,
    MemberVO,
    MessageVO,
    RoomDetail,
    RoomListItem,
    RoomTokenVO,
    RoomVO,
    TransferHostResult,
)
from app.services import livekit as livekit_service
from app.security.ids import new_code, new_id

logger = logging.getLogger("app")

ROOM_CODE_RETRIES = 3
RECENT_MESSAGE_LIMIT = 20
DEFAULT_CAPACITY = 8
HOST_ROLES = ("host",)
MANAGER_ROLES = ("host", "moderator")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_livekit(call) -> bool:
    """外部调用兜底：LiveKit 层已自带 try/except，这里再加一层，保证任何异常都不影响已提交的库状态。

    返回外部调用是否成功（`livekitApplied`）；失败只记日志（ADR-0011 条 4）。
    """
    try:
        return bool(call())
    except Exception as exc:  # noqa: BLE001
        logger.warning("LiveKit 外部调用异常（库状态已提交，不回滚）：%s: %s", type(exc).__name__, exc)
        return False


def _room_vo(
    item: RoomWithHost,
    member_count: int,
    pending_count: int,
    my_role: Optional[str] = None,
    my_request_status: Optional[str] = None,
    livekit_applied: Optional[bool] = None,
) -> RoomVO:
    """房间行 + 聚合 → VO（列表与详情的唯一组装点；`livekit_applied` 仅触达外部服务的动作会带）。"""
    room = item.room
    return RoomVO(
        id=room.id,
        topic=room.topic,
        topic_label=room.topic_label,
        title=room.title,
        description=room.description,
        status=room.status,
        phase="ended" if room.status == "ended" else "active.idle",  # M2 再接 LiveKit 在场信息补 in_session
        capacity=room.capacity,
        room_code=room.room_code,
        host_id=room.host_id,
        host_name=item.host_name,
        member_count=member_count,
        pending_count=pending_count,
        my_role=my_role,
        my_request_status=my_request_status,
        created_at=room.created_at,
        ended_at=room.ended_at,
        livekit_applied=livekit_applied,
    )


def _visible_pending_count(my_role: Optional[str], pending_count: int) -> int:
    """待批申请数只对房主/协管有意义（功能页 FQ-4：服务端强制，非管理者一律返回 0）。"""
    return pending_count if my_role in MANAGER_ROLES else 0


def _member_vo(item: repo.MemberRowWithName) -> MemberVO:
    member = item.member
    return MemberVO(
        id=member.id,
        user_id=member.user_id,
        display_name=item.display_name,
        role=member.role,
        status=member.status,
        exit_reason=member.exit_reason,
        joined_at=member.joined_at,
        left_at=member.left_at,
    )


def _request_vo(item: repo.JoinRequestRowWithName) -> JoinRequestVO:
    request = item.request
    return JoinRequestVO(
        id=request.id,
        room_id=request.room_id,
        user_id=request.user_id,
        display_name=item.display_name,
        message=request.message,
        status=request.status,
        created_at=request.created_at,
        decided_at=request.decided_at,
        decided_by=request.decided_by,
    )


def assert_room_active(room: Optional[RoomRow]) -> RoomRow:
    """存在否则 `NOT_FOUND`；`active` 否则 `ROOM_ENDED`（前置拦截按此顺序）。"""
    if room is None:
        raise AppError(ERR_NOT_FOUND, "房间不存在", status=404)
    if room.status != "active":
        raise AppError(ERR_ROOM_ENDED, "该房间已结束，仅可查看历史内容", status=409)
    return room


def assert_room_role(conn: Connection, actor: Optional[UserVO], room_id: str, allowed: Sequence[str]) -> MemberRow:
    """未登录 `UNAUTHORIZED`；非活跃成员 / 角色不符 `FORBIDDEN`。"""
    if actor is None:
        raise AppError(ERR_UNAUTHORIZED, "请先登录", status=401)
    member = repo.get_active_member(conn, room_id, actor.id)
    if member is None or member.role not in allowed:
        raise AppError(ERR_FORBIDDEN, "你没有该操作的权限", status=403)
    return member


def assert_manager_role(conn: Connection, actor: Optional[UserVO], room: RoomRow) -> None:
    """申请列表的可见性判定。

    活跃的 host/moderator 可看；房间已结束时（成员都已 inactive）允许**房主与历史协管**追溯查看，
    与功能页 F-05「房间结束后仍可查看」一致。
    """
    if actor is None:
        raise AppError(ERR_UNAUTHORIZED, "请先登录", status=401)
    member = repo.get_active_member(conn, room.id, actor.id)
    if member is not None and member.role in MANAGER_ROLES:
        return
    if room.status == "ended":
        if room.host_id == actor.id:
            return
        for item in repo.list_members(conn, room.id, include_inactive=True):
            if item.member.user_id == actor.id and item.member.role in MANAGER_ROLES:
                return
    raise AppError(ERR_FORBIDDEN, "你没有该操作的权限", status=403)


# ---------------- 建房 / 列表 / 详情 ----------------

def create_room(conn: Connection, actor: UserVO, data: CreateRoomIn) -> RoomVO:
    """建房 + 自动写入 Host 成员；房间码冲突重试 3 次。"""
    room_id = new_id("room")
    last_error: Optional[Exception] = None
    for _ in range(ROOM_CODE_RETRIES):
        try:
            with conn.transaction():
                repo.insert_room(
                    conn,
                    repo.NewRoom(
                        id=room_id,
                        host_id=actor.id,
                        topic=data.topic,
                        topic_label=data.topic_label,
                        title=data.title,
                        description=data.description,
                        capacity=DEFAULT_CAPACITY,
                        room_code=new_code(),
                    ),
                )
                repo.insert_member(conn, repo.NewMember(id=new_id("mem"), room_id=room_id, user_id=actor.id, role="host"))
            break
        except UniqueViolation as exc:  # room_code 撞车（极小概率）
            last_error = exc
            continue
    else:
        logger.warning("房间码连续 %s 次冲突，放弃建房", ROOM_CODE_RETRIES)
        raise AppError(ERR_INTERNAL, "创建房间失败，请重试", status=500) from last_error

    created = repo.get_room(conn, room_id)
    if created is None:
        raise AppError(ERR_INTERNAL, "创建房间后无法读取", status=500)
    return _room_vo(created, member_count=1, pending_count=0, my_role="host")


def list_rooms(conn: Connection, actor: Optional[UserVO], f: repo.RoomFilter) -> tuple[list[RoomListItem], int]:
    """列表 + 总数；批量取聚合与我方状态，避免 N+1。"""
    items, total = repo.list_rooms(conn, f)
    room_ids = [item.room.id for item in items]
    aggregates = repo.room_aggregates(conn, room_ids)
    roles = repo.my_active_roles(conn, actor.id, room_ids) if actor else {}
    pending = repo.my_pending_requests(conn, actor.id, room_ids) if actor else set()
    result: list[RoomListItem] = []
    for item in items:
        member_count, pending_count = aggregates.get(item.room.id, (0, 0))
        my_role = roles.get(item.room.id)
        result.append(
            RoomListItem(
                **_room_vo(
                    item,
                    member_count=member_count,
                    pending_count=_visible_pending_count(my_role, pending_count),
                    my_role=my_role,
                    my_request_status="pending" if item.room.id in pending else None,
                ).model_dump()
            )
        )
    return result, total


def get_room_detail(conn: Connection, actor: Optional[UserVO], room_id: str) -> RoomDetail:
    """房间 + 成员 + 最近 20 条消息 + 我的状态；不存在抛 `NOT_FOUND`。"""
    item = repo.get_room(conn, room_id)
    if item is None:
        raise AppError(ERR_NOT_FOUND, "房间不存在", status=404)
    aggregates = repo.room_aggregates(conn, [room_id])
    member_count, pending_count = aggregates.get(room_id, (0, 0))
    roles = repo.my_active_roles(conn, actor.id, [room_id]) if actor else {}
    pending = repo.my_pending_requests(conn, actor.id, [room_id]) if actor else set()
    my_role = roles.get(room_id)
    room = _room_vo(
        item,
        member_count=member_count,
        pending_count=_visible_pending_count(my_role, pending_count),
        my_role=my_role,
        my_request_status="pending" if room_id in pending else None,
    )
    include_inactive = room.status == "ended"  # 结束后展示历史成员与退出原因（功能页 F-09/F-12）
    members = [_member_vo(m) for m in repo.list_members(conn, room_id, include_inactive=include_inactive)]
    messages = [
        MessageVO(
            id=m.message.id,
            user_id=m.message.user_id,
            display_name=m.display_name,
            body=m.message.body,
            kind=m.message.kind,
            created_at=m.message.created_at,
        )
        for m in repo.list_recent_messages(conn, room_id, RECENT_MESSAGE_LIMIT)
    ]
    return RoomDetail(room=room, members=members, messages=messages)


def derive_room_phase(conn: Connection, room_id: str) -> str:
    """派生相位（不落库）：M1 只区分 `active.idle` / `ended`；M2 接 LiveKit 在场信息补 `active.in_session`。"""
    item = repo.get_room(conn, room_id)
    if item is None:
        raise AppError(ERR_NOT_FOUND, "房间不存在", status=404)
    return "ended" if item.room.status == "ended" else "active.idle"


# ---------------- 加入申请 ----------------

def request_join(conn: Connection, actor: UserVO, room_id: str, message: str) -> JoinRequestVO:
    """提交申请：五种拦截（未登录在依赖层）→ 写申请；唯一冲突映射为 `ALREADY_PENDING`。"""
    item = repo.get_room(conn, room_id)
    room = assert_room_active(item.room if item else None)
    if repo.get_active_member(conn, room_id, actor.id) is not None:
        raise AppError(ERR_ALREADY_MEMBER, "你已在房间中", status=409)
    if repo.get_pending_request(conn, room_id, actor.id) is not None:
        raise AppError(ERR_ALREADY_PENDING, "你已提交过申请，请等待房主处理", status=409)
    if repo.count_active_members(conn, room_id) >= room.capacity:
        raise AppError(ERR_ROOM_FULL, f"房间已满（上限 {room.capacity} 人）", status=409)

    request_id = new_id("req")
    try:
        with conn.transaction():
            repo.insert_join_request(conn, repo.NewJoinRequest(id=request_id, room_id=room_id, user_id=actor.id, message=message))
    except UniqueViolation as exc:  # 并发双击
        raise AppError(ERR_ALREADY_PENDING, "你已提交过申请，请等待房主处理", status=409) from exc
    created = repo.get_join_request(conn, request_id)
    if created is None:
        raise AppError(ERR_INTERNAL, "提交申请后无法读取", status=500)
    return _request_vo(repo.JoinRequestRowWithName(created, actor.display_name))


def list_join_requests(conn: Connection, actor: UserVO, room_id: str, status: Optional[str]) -> list[JoinRequestVO]:
    """申请列表（Host/Moderator）；房间可 `ended`，只读。"""
    item = repo.get_room(conn, room_id)
    if item is None:
        raise AppError(ERR_NOT_FOUND, "房间不存在", status=404)
    assert_manager_role(conn, actor, item.room)
    return [_request_vo(r) for r in repo.list_join_requests(conn, room_id, status)]


def withdraw_join_request(conn: Connection, actor: UserVO, request_id: str) -> JoinRequestVO:
    """撤回申请：仅本人可撤回，且只有 `pending` 可撤回（否则 `CONFLICT`）。撤回后可立即再次申请。"""
    request = repo.get_join_request(conn, request_id)
    if request is None:
        raise AppError(ERR_NOT_FOUND, "申请不存在", status=404)
    if request.user_id != actor.id:
        raise AppError(ERR_FORBIDDEN, "只能撤回自己的申请", status=403)
    with conn.transaction():
        repo.lock_room(conn, request.room_id)
        current = repo.get_join_request(conn, request_id)
        if current is None or current.status != "pending":
            raise AppError(ERR_CONFLICT, "该申请已被处理", status=409)
        repo.withdraw_join_request(conn, request_id, _now(), actor.id)
    withdrawn = repo.get_join_request(conn, request_id)
    if withdrawn is None:
        raise AppError(ERR_INTERNAL, "撤回后无法读取结果", status=500)
    return _request_vo(repo.JoinRequestRowWithName(withdrawn, actor.display_name))


def approve_join_request(conn: Connection, actor: UserVO, request_id: str) -> ApprovalResult:
    """批准：锁房间行 → 房间 active → 申请 pending → 人数 < capacity → 写成员 + 落决定（同一事务）。"""
    request = repo.get_join_request(conn, request_id)
    if request is None:
        raise AppError(ERR_NOT_FOUND, "申请不存在", status=404)
    with conn.transaction():
        room_row = repo.lock_room(conn, request.room_id)
        room = assert_room_active(room_row)
        assert_room_role(conn, actor, request.room_id, MANAGER_ROLES)
        current = repo.get_join_request(conn, request_id)
        if current is None or current.status != "pending":
            raise AppError(ERR_CONFLICT, "该申请已被处理", status=409)
        if repo.count_active_members(conn, request.room_id) >= room.capacity:
            raise AppError(ERR_ROOM_FULL, f"房间已满（上限 {room.capacity} 人）", status=409)
        if repo.get_active_member(conn, request.room_id, request.user_id) is not None:
            raise AppError(ERR_ALREADY_MEMBER, "该用户已在房间中", status=409)
        member_id = new_id("mem")
        repo.insert_member(
            conn, repo.NewMember(id=member_id, room_id=request.room_id, user_id=request.user_id, role="participant")
        )
        repo.decide_join_request(conn, request_id, "approved", actor.id, _now())
    approved = repo.get_join_request(conn, request_id)
    members = repo.list_members(conn, request.room_id, include_inactive=True)
    new_member = next((m for m in members if m.member.id == member_id), None)
    if approved is None or new_member is None:
        raise AppError(ERR_INTERNAL, "批准后无法读取结果", status=500)
    return ApprovalResult(request=_request_vo(repo.JoinRequestRowWithName(approved, new_member.display_name)), member=_member_vo(new_member))


def reject_join_request(conn: Connection, actor: UserVO, request_id: str) -> JoinRequestVO:
    """拒绝：锁房间行 → 房间 active → 申请 pending → 落决定。"""
    request = repo.get_join_request(conn, request_id)
    if request is None:
        raise AppError(ERR_NOT_FOUND, "申请不存在", status=404)
    with conn.transaction():
        room_row = repo.lock_room(conn, request.room_id)
        assert_room_active(room_row)
        assert_room_role(conn, actor, request.room_id, MANAGER_ROLES)
        current = repo.get_join_request(conn, request_id)
        if current is None or current.status != "pending":
            raise AppError(ERR_CONFLICT, "该申请已被处理", status=409)
        repo.decide_join_request(conn, request_id, "rejected", actor.id, _now())
    rejected = repo.get_join_request(conn, request_id)
    applicant = get_user_by_id(conn, request.user_id)
    if rejected is None:
        raise AppError(ERR_INTERNAL, "拒绝后无法读取结果", status=500)
    return _request_vo(repo.JoinRequestRowWithName(rejected, applicant.display_name if applicant else ""))


def leave_room(conn: Connection, actor: UserVO, room_id: str) -> None:
    """离开：锁房间行 → 房间 active → 是活跃成员 → 非 Host → 置 `inactive/self_leave`。"""
    with conn.transaction():
        room_row = repo.lock_room(conn, room_id)
        assert_room_active(room_row)
        member = repo.get_active_member(conn, room_id, actor.id)
        if member is None:
            raise AppError(ERR_NOT_MEMBER, "你不在该房间中", status=409)
        if member.role == "host":
            raise AppError(ERR_HOST_CANNOT_LEAVE, "房主不能直接离开，请先结束房间或移交房主", status=409)
        repo.deactivate_member(conn, room_id, actor.id, "self_leave", _now())


def end_room(conn: Connection, actor: UserVO, room_id: str) -> RoomVO:
    """结束房间：锁房间行 → 仅 Host → 房间 active → 三项连带动作（同事务）。"""
    with conn.transaction():
        room_row = repo.lock_room(conn, room_id)
        assert_room_active(room_row)
        assert_room_role(conn, actor, room_id, HOST_ROLES)
        ended_at = _now()
        repo.update_room_ended(conn, room_id, ended_at)
        repo.deactivate_all_members(conn, room_id, ended_at)
        repo.cancel_pending_requests(conn, room_id, ended_at)
    # 外部调用一律在事务提交之后（ADR-0011 条 4）：失败不回滚库状态，用 livekit_applied 如实上报
    livekit_applied = _safe_livekit(lambda: livekit_service.delete_room(room_id))
    item = repo.get_room(conn, room_id)
    if item is None:
        raise AppError(ERR_INTERNAL, "结束后无法读取房间", status=500)
    aggregates = repo.room_aggregates(conn, [room_id])
    member_count, pending_count = aggregates.get(room_id, (0, 0))
    return _room_vo(
        item, member_count=member_count, pending_count=pending_count, my_role="host", livekit_applied=livekit_applied
    )


# ---------------- 实时房间（r002，LiveKit） ----------------

def issue_room_token(conn: Connection, actor: Optional[UserVO], room_id: str) -> RoomTokenVO:
    """取进房 Token。

    拦截顺序：未登录 401 → 房间不存在 404 → 已结束 409 `ROOM_ENDED` → 非活跃成员 403 `NOT_MEMBER`。
    `identity` 用 `actor.id`（ADR-0011 条 2 的「identity 唯一」），签票是**本地签名**、不联网。
    """
    if actor is None:
        raise AppError(ERR_UNAUTHORIZED, "请先登录", status=401)
    room = repo.get_room(conn, room_id)
    if room is None:
        raise AppError(ERR_NOT_FOUND, "房间不存在", status=404)
    if room.room.status != "active":
        raise AppError(ERR_ROOM_ENDED, "该房间已结束，仅可查看历史内容", status=409)
    member = repo.get_active_member(conn, room_id, actor.id)
    if member is None:
        raise AppError(ERR_NOT_MEMBER, "你不在该房间中（或已被移出）", status=403)
    settings = load_settings()
    token = livekit_service.issue_token(
        room_id,
        actor.id,
        actor.display_name,
        member.role,
        settings=settings,
        max_participants=room.room.capacity,
    )
    return RoomTokenVO(
        token=token,
        url=settings.livekit_url,
        room_name=room_id,
        expires_in=settings.livekit_token_ttl_seconds,
    )


def kick_member(conn: Connection, actor: Optional[UserVO], room_id: str, user_id: str) -> KickResult:
    """移出成员（Host 任意；Moderator 只能移出普通参与者）。

    库侧置 `inactive/kicked` 与外部移除**不在同一事务**：外部调用在提交后执行，失败不回滚（ADR-0011 条 4）。
    """
    if actor is None:
        raise AppError(ERR_UNAUTHORIZED, "请先登录", status=401)
    if actor.id == user_id:
        raise AppError(ERR_VALIDATION, "不能移出自己（房主请用「结束房间」，其他人请用「离开房间」）", status=400)
    with conn.transaction():
        room_row = repo.lock_room(conn, room_id)
        assert_room_active(room_row)
        actor_member = assert_room_role(conn, actor, room_id, MANAGER_ROLES)
        target = repo.get_active_member(conn, room_id, user_id)
        if target is None:
            raise AppError(ERR_NOT_MEMBER, "该用户不在房间中", status=409)
        if target.role == "host":
            raise AppError(ERR_FORBIDDEN, "不能移出房主", status=403)
        if target.role == "moderator" and actor_member.role == "moderator":
            raise AppError(ERR_FORBIDDEN, "协管不能移出协管", status=403)
        repo.deactivate_member(conn, room_id, user_id, "kicked", _now())
    livekit_applied = _safe_livekit(lambda: livekit_service.remove_participant(room_id, user_id))
    item = next((m for m in repo.list_members(conn, room_id, include_inactive=True) if m.member.user_id == user_id), None)
    if item is None:
        raise AppError(ERR_INTERNAL, "移出后无法读取成员", status=500)
    return KickResult(member=_member_vo(item), livekit_applied=livekit_applied)


def set_member_role(conn: Connection, actor: Optional[UserVO], room_id: str, user_id: str, role: str) -> MemberVO:
    """任命 / 取消协管（仅 Host；不用于房主移交）。"""
    if actor is None:
        raise AppError(ERR_UNAUTHORIZED, "请先登录", status=401)
    if role not in ("moderator", "participant"):
        raise AppError(ERR_VALIDATION, "角色只能是 moderator 或 participant", status=400)
    if actor.id == user_id:
        raise AppError(ERR_VALIDATION, "不能修改自己的角色（房主移交请用「移交房主」）", status=400)
    with conn.transaction():
        room_row = repo.lock_room(conn, room_id)
        assert_room_active(room_row)
        assert_room_role(conn, actor, room_id, HOST_ROLES)
        target = repo.get_active_member(conn, room_id, user_id)
        if target is None:
            raise AppError(ERR_NOT_MEMBER, "该用户不在房间中", status=409)
        if target.role == "host":
            raise AppError(ERR_FORBIDDEN, "房主角色不能通过该接口修改", status=403)
        repo.update_member_role(conn, room_id, user_id, role)
    item = next((m for m in repo.list_members(conn, room_id) if m.member.user_id == user_id), None)
    if item is None:
        raise AppError(ERR_INTERNAL, "改角色后无法读取成员", status=500)
    return _member_vo(item)


def transfer_host(conn: Connection, actor: Optional[UserVO], room_id: str, new_host_id: str) -> TransferHostResult:
    """移交房主：原 Host 降为 Moderator、目标升为 Host、`rooms.host_id` 改写（同一事务）。

    不调用 LiveKit（旧 Token 的 `room_admin` 到 TTL 为止；ADR-0011 §8.8 已知取舍）。
    """
    if actor is None:
        raise AppError(ERR_UNAUTHORIZED, "请先登录", status=401)
    if actor.id == new_host_id:
        raise AppError(ERR_VALIDATION, "不能把房主移交给自己", status=400)
    with conn.transaction():
        room_row = repo.lock_room(conn, room_id)
        assert_room_active(room_row)
        assert_room_role(conn, actor, room_id, HOST_ROLES)
        target = repo.get_active_member(conn, room_id, new_host_id)
        if target is None:
            raise AppError(ERR_NOT_MEMBER, "该用户不在房间中", status=409)
        repo.update_member_role(conn, room_id, actor.id, "moderator")
        repo.update_member_role(conn, room_id, new_host_id, "host")
        repo.update_room_host(conn, room_id, new_host_id)
        if repo.count_active_hosts(conn, room_id) != 1:  # 不变量：活跃 Host 恒为 1
            raise AppError(ERR_INTERNAL, "移交后活跃房主数量异常", status=500)
    room = repo.get_room(conn, room_id)
    if room is None:
        raise AppError(ERR_INTERNAL, "移交后无法读取房间", status=500)
    members = {m.member.user_id: m for m in repo.list_members(conn, room_id)}
    previous, new_host = members.get(actor.id), members.get(new_host_id)
    if previous is None or new_host is None:
        raise AppError(ERR_INTERNAL, "移交后无法读取成员", status=500)
    aggregates = repo.room_aggregates(conn, [room_id])
    member_count, pending_count = aggregates.get(room_id, (0, 0))
    return TransferHostResult(
        room=_room_vo(room, member_count=member_count, pending_count=pending_count, my_role="moderator"),
        previous_host=_member_vo(previous),
        new_host=_member_vo(new_host),
    )
