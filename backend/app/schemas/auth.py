"""账户模块的请求/响应模型（Pydantic v2）。

设计事实源：docs/01-architecture/r001-app-architecture.md §8、§9.4
出参一律走 VO，不吐库行（`UserRow` 含 `password_hash`，任何情况下都不得进响应）。
"""
from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator

from app.schemas.common import CamelModel, validate_email

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128


class RegisterIn(CamelModel):
    email: str = Field(description="登录邮箱，大小写不敏感")
    display_name: str = Field(min_length=1, max_length=32, description="显示名（1~32 字）")
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return validate_email(value)

    @field_validator("display_name")
    @classmethod
    def _display_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("显示名不能为空")
        return stripped


class LoginIn(CamelModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return validate_email(value)


class UserVO(CamelModel):
    """对外暴露的用户视图（不含任何口令材料）。

    r012：新增 `role`（`'user'` / `'superadmin'`）——前端据此显示「管理后台」入口；
    超管的隐身/旁路校验一律在服务端强制执行，前端可见性只是体验（不做安全边界）。
    """

    id: str
    email: str
    display_name: str
    role: str = "user"
    created_at: datetime
