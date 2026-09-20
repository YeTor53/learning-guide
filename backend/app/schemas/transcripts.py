"""转写相关的 VO（r010）。

设计事实源：`docs/rounds/r010-transcription/design.md` §2.4/§2.5；契约对齐官方 `TranscriptionSegment`（ADR-0022 D3）。
"""
from __future__ import annotations

from datetime import datetime

from app.schemas.common import CamelModel


class TranscriptVO(CamelModel):
    """一段最终稿转写（对外字段 camelCase；`speakerName` 由服务层补齐）。"""

    id: str
    room_id: str
    speaker_id: str
    speaker_name: str
    segment_index: int
    text: str
    language: str
    started_at: datetime
    duration_ms: int
    final: bool = True
    provider: str = ""
    model: str = ""
    created_at: datetime
