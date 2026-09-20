"""纪要相关的 VO（r008）。

设计事实源：`docs/rounds/r008-assignment-gaps/design.md` §2.1；一条房间一份、覆盖式重生（ADR-0018）。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.schemas.common import CamelModel


class SessionSummaryVO(CamelModel):
    id: str
    room_id: str
    status: str
    provider: str
    model: str
    input_digest: str
    content: str
    error: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
