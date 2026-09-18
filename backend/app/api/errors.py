"""业务错误载体与全局异常处理器（骨架层）。

设计事实源：docs/01-architecture/r001-app-architecture.md §8（错误码总表）、§9.5、§13
约定：service 层只抛 AppError，不接触 HTTP 对象；路由层与全局处理器负责翻译成信封。
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError

from app.api.envelope import fail

logger = logging.getLogger("app")

# 错误码总表（r001）。M2 增 INVITE_INVALID；M4 增 SUMMARY_FAILED / LLM_NOT_CONFIGURED。
ERR_VALIDATION = "VALIDATION"
ERR_UNAUTHORIZED = "UNAUTHORIZED"
ERR_INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
ERR_FORBIDDEN = "FORBIDDEN"
ERR_NOT_FOUND = "NOT_FOUND"
ERR_EMAIL_TAKEN = "EMAIL_TAKEN"
ERR_ALREADY_MEMBER = "ALREADY_MEMBER"
ERR_ALREADY_PENDING = "ALREADY_PENDING"
ERR_CONFLICT = "CONFLICT"
ERR_NOT_MEMBER = "NOT_MEMBER"
ERR_HOST_CANNOT_LEAVE = "HOST_CANNOT_LEAVE"
ERR_ROOM_ENDED = "ROOM_ENDED"
ERR_ROOM_FULL = "ROOM_FULL"
ERR_CONFIG_MISSING = "CONFIG_MISSING"
ERR_INTERNAL = "INTERNAL"


class AppError(Exception):
    """业务错误：`code` 是错误码，`status` 是 HTTP 状态码，`message` 直接可展示。"""

    def __init__(self, code: str, message: str = "", status: int = 400) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.status = status


def register_error_handlers(app: FastAPI) -> None:
    """把三类异常翻译成统一信封；未预期异常不回显内部细节（§13）。"""

    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError):
        return fail(exc.code, exc.message, exc.status)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        first = exc.errors()[0] if exc.errors() else {}
        loc = ".".join(str(p) for p in first.get("loc", ()) if p != "body")
        message = f"参数不合法：{loc} {first.get('msg', '')}".strip() if loc else "参数不合法"
        return fail(ERR_VALIDATION, message, 400)

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception):
        logger.exception("未预期异常 %s %s", request.method, request.url.path)
        return fail(ERR_INTERNAL, "服务器内部错误", 500)
