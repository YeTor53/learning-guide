"""管理后台的请求/响应模型（r012）。

设计事实源：docs/rounds/r012-superadmin-console/design.md §3.3（出参一律 camelCase）。
分页沿用 `schemas/common.py::LimitOffset`（默认 20 / 上限 100）。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.schemas.common import CamelModel


class AdminRoomItem(CamelModel):
    id: str
    title: str
    topic_label: str
    status: str
    capacity: int
    room_code: str
    host_id: str
    host_name: str
    member_count: int
    pending_count: int
    summary_status: Optional[str] = None
    created_at: datetime
    ended_at: Optional[datetime] = None


class AdminUserItem(CamelModel):
    id: str
    email: str
    display_name: str
    role: str
    created_at: datetime
    last_seen_at: Optional[datetime] = None
    active_rooms: int
    message_count: int
    global_message_count: int


class AdminSummaryItem(CamelModel):
    id: str
    room_id: str
    room_title: str
    status: str
    provider: str
    model: str
    content_length: int
    error: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AdminAuditItem(CamelModel):
    id: str
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    action: str
    target_type: str
    target_id: str
    detail: dict
    created_at: datetime

