"""公共请求/响应模型与共用的规范化函数。

设计事实源：docs/01-architecture/r001-app-architecture.md §8（接口约定）
"""
from __future__ import annotations

import re
from typing import NamedTuple

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class CamelModel(BaseModel):
    """对外模型基类：字段内部 snake_case，JSON 一律 camelCase（请求体两种写法都接受）。

    所有模块共用同一约定，前端只按 camelCase 取值（账户与房间两套 VO 口径一致）。
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Page(NamedTuple):
    """列表接口的分页元信息（`?limit=&offset=`，默认 20、上限 100）。"""

    total: int
    limit: int
    offset: int


class ErrorOut(BaseModel):
    code: str
    message: str


def normalize_email(value: str) -> str:
    """去首尾空白并统一小写；注册与登录共用，避免两处口径不一致。"""
    return value.strip().lower()


def validate_email(value: str) -> str:
    """基础格式校验（不引第三方 `email-validator`，保持依赖最少）。"""
    normalized = normalize_email(value)
    if len(normalized) > 254 or not EMAIL_RE.match(normalized):
        raise ValueError("邮箱格式不正确")
    return normalized


class LimitOffset(BaseModel):
    """分页查询参数（列表接口依赖注入用）。"""

    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
