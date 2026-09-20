"""全服大屏聊天的请求/响应模型（r012）。

设计事实源：docs/rounds/r012-superadmin-console/design.md §4；口径：单条 1~500 字。
"""
from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator

from app.schemas.common import CamelModel

BODY_MAX = 500


class GlobalMessageIn(CamelModel):
    body: str = Field(min_length=1, max_length=BODY_MAX, description="正文（1~500 字）")

    @field_validator("body")
    @classmethod
    def _body(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("不能发送空消息")
        return stripped


class GlobalMessageVO(CamelModel):
    id: str
    user_id: str
    display_name: str
    body: str
    author_online: bool
    created_at: datetime
