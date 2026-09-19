"""房间模块的请求/响应模型（Pydantic v2，JSON 字段用 camelCase）。

设计事实源：docs/02-modules/r001-rooms.md §5（接口清单）、§6.6；功能页 §3（界面字段）
约定：数据库列是 snake_case，对外 JSON 用 camelCase（前后端都按 camelCase 交流）；
      出参只暴露 VO，不吐库行。
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import Field

from app.schemas.common import CamelModel

TopicLiteral = Literal["epicureanism", "math-biology", "german-history", "philosophy-history", "chinese-philosophy", "ethics", "modern-history", "ancient-china", "mathematical-analysis", "linear-algebra", "probability-statistics", "number-theory", "machine-learning", "custom"]
TOPICS: tuple[str, ...] = (
    "epicureanism",
    "math-biology",
    "german-history",
    "philosophy-history",
    "chinese-philosophy",
    "ethics",
    "modern-history",
    "ancient-china",
    "mathematical-analysis",
    "linear-algebra",
    "probability-statistics",
    "number-theory",
    "machine-learning",
    "custom",
)
MEMBER_ROLES = ("host", "moderator", "participant")


class CreateRoomIn(CamelModel):
    topic: TopicLiteral
    topic_label: str = Field(min_length=1, max_length=32, description="展示用主题名（自定义主题时由用户填）")
    title: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)


class JoinRequestIn(CamelModel):
    message: str = Field(default="", max_length=200)


class FocusRequestVO(CamelModel):
    """协管焦点申请（r009）。"""

    id: str
    room_id: str
    requester_id: str
    requester_name: str
    status: str
    decided_by: Optional[str] = None
    created_at: datetime
    decided_at: Optional[datetime] = None


class RoomVO(CamelModel):
    id: str
    topic: str
    topic_label: str
    title: str
    description: str
    status: str
    phase: str
    capacity: int
    room_code: str
    host_id: str
    host_name: str
    member_count: int
    pending_count: int
    my_role: Optional[str] = None
    my_request_status: Optional[str] = None
    my_request_id: Optional[str] = None
    my_role_any: Optional[str] = None
    """我在本房的角色（**含已失效的成员身份**）——房间结束后 `my_role` 为空，但纪要等追溯动作仍需要它（r008）。"""
    """我在这间房的待批申请 id（本人可见；撤回用——r007 修：原来前端去调管理权限的申请列表接口，申请人一律 403）。"""
    created_at: datetime
    ended_at: Optional[datetime] = None
    livekit_applied: Optional[bool] = None
    """仅「结束房间」等触达外部服务的响应会带上：外部调用是否成功（失败不回滚库状态，ADR-0011 条 4）。"""


class RoomListItem(RoomVO):
    """列表项：字段与 `RoomVO` 相同；独立类型便于前端与后续轮次演进。"""


class MemberVO(CamelModel):
    id: str
    user_id: str
    display_name: str
    role: str
    status: str
    exit_reason: Optional[str] = None
    joined_at: datetime
    left_at: Optional[datetime] = None


class MessageVO(CamelModel):
    id: str
    user_id: str
    display_name: str
    body: str
    kind: str
    created_at: datetime


class JoinRequestVO(CamelModel):
    id: str
    room_id: str
    user_id: str
    display_name: str
    message: str
    status: str
    created_at: datetime
    decided_at: Optional[datetime] = None
    decided_by: Optional[str] = None


class RoomDetail(CamelModel):
    room: RoomVO
    members: list[MemberVO]
    messages: list[MessageVO]


class ApprovalResult(CamelModel):
    request: JoinRequestVO
    member: MemberVO


class RoomTokenVO(CamelModel):
    """进房 Token（前端拿它连 LiveKit；Server Secret 永不出现在响应里）。"""

    token: str
    url: str
    room_name: str
    expires_in: int


class RoleIn(CamelModel):
    """任命 / 取消协管：只允许在 moderator 与 participant 之间切换（房主移交走单独接口）。"""

    role: Literal["moderator", "participant"]


class TransferHostIn(CamelModel):
    user_id: str = Field(min_length=1)


class KickResult(CamelModel):
    """移出成员：库侧结果 + 外部调用是否成功。"""

    member: MemberVO
    livekit_applied: bool


class TransferHostResult(CamelModel):
    """移交房主：库侧结果（**不同步 LiveKit 权限**——旧 Token 的 `room_admin` 到 TTL 为止，ADR-0011 §8.8）。"""

    room: RoomVO
    previous_host: MemberVO
    new_host: MemberVO

# ---------------- r004（M3）房内扩展能力 ----------------
# 设计事实源：docs/rounds/r004-room-extras/design.md §4

class MessageIn(CamelModel):
    """发消息：trim 后 1~500 字（空串与超长由 schema 拦成 400 VALIDATION）。"""

    body: str = Field(min_length=1, max_length=500)


class HandVO(CamelModel):
    id: str
    user_id: str
    display_name: str
    raised_at: datetime


class FocusVO(CamelModel):
    """当前焦点：`subjectUserId=None` 表示无焦点（或已被取消）。"""

    subject_user_id: Optional[str] = None
    subject_name: Optional[str] = None
    actor_user_id: Optional[str] = None
    set_at: Optional[datetime] = None


class FocusIn(CamelModel):
    """设/取消焦点：`userId=None` 表示取消。"""

    user_id: Optional[str] = None
