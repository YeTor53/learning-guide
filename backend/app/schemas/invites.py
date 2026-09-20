"""限时邀请的入参与 VO（r008）。

设计事实源：`docs/rounds/r008-assignment-gaps/design.md` §2；决定见 ADR-0019。
口径（用户 2026-09-19）：**有效期最长 1 分钟**（默认 60 秒，上限由 `INVITE_TTL_MAX_SECONDS` 单点可调）；默认 1 次可用。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.common import CamelModel


class InviteCreateIn(CamelModel):
    ttl_seconds: int = Field(default=60, ge=10, le=86400, description="有效期秒数（默认 60，上限见 INVITE_TTL_MAX_SECONDS）")
    max_uses: int = Field(default=1, ge=1, le=50, description="最多可用次数")


class InviteVO(CamelModel):
    id: str
    room_id: str
    code: str
    expires_at: datetime
    max_uses: int
    used_count: int
    created_at: datetime
    expired: bool


class InviteAcceptResult(CamelModel):
    room_id: str
    """凭码加入后的房间 id（前端据此直接进交流页）。"""
    created: bool
    """true = 本次新建在册成员；false = 已在册（幂等）。"""
    display_name: Optional[str] = None
