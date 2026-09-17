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

TopicLiteral = Literal["epicureanism", "math-biology", "german-history", "custom"]
TOPICS: tuple[str, ...] = ("epicureanism", "math-biology", "german-history", "custom")
MEMBER_ROLES = ("host", "moderator", "participant")


class CreateRoomIn(CamelModel):
    topic: TopicLiteral
    topic_label: str = Field(min_length=1, max_length=32, description="展示用主题名（自定义主题时由用户填）")
    title: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)


class JoinRequestIn(CamelModel):
    message: str = Field(default="", max_length=200)


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
    created_at: datetime
    ended_at: Optional[datetime] = None


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
