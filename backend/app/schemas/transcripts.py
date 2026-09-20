"""转写相关的 VO 与请求模型（r010）。

设计事实源：`docs/rounds/r010-transcription/design.md` §2.4/§9.3.4；决定见 ADR-0023（换轨后前端回传最终稿文本段）。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.common import CamelModel


class TranscriptVO(CamelModel):
    """一段最终稿转写（对外字段 camelCase；`speakerName` 由服务层补齐）。"""

    id: str
    room_id: str
    speaker_id: str
    speaker_name: str
    segment_index: Optional[int] = None
    text: str
    language: str
    started_at: datetime
    duration_ms: int
    final: bool = True
    provider: str = ""
    model: str = ""
    external_id: Optional[str] = None
    created_at: datetime


class SegmentIn(CamelModel):
    """A 路径：前端回传的一段转写（只回传最终稿；`final=false` 服务端直接丢弃）。

    `externalId` = 官方 `TranscriptionSegment.id`（幂等键）；`speakerIdentity` = LiveKit participant identity，
    本项目里**就是 `user_id`**（ADR-0011 条 2），故可直接当说话人。
    """

    external_id: str = Field(min_length=1, max_length=128)
    speaker_identity: str = Field(min_length=1, max_length=64)
    text: str = Field(min_length=1, max_length=2000)
    started_at: datetime
    duration_ms: int = Field(default=0, ge=0)
    language: str = Field(default="zh", max_length=16)
    final: bool = True
