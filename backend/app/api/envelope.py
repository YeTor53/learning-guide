"""统一响应信封（骨架层）。

设计事实源：docs/01-architecture/r001-app-architecture.md §8
成功：{"ok": true,  "data": {...}}
失败：{"ok": false, "error": {"code": "...", "message": "..."}}
"""
from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse


def ok(data: Any = None, status: int = 200) -> JSONResponse:
    """成功信封。`status` 默认 200；创建类接口传 201。"""
    return JSONResponse(status_code=status, content={"ok": True, "data": data})


def fail(code: str, message: str, status: int = 400) -> JSONResponse:
    """失败信封。`code` 取架构页 §8 错误码总表；`message` 是给用户看的中文提示。"""
    return JSONResponse(status_code=status, content={"ok": False, "error": {"code": code, "message": message}})
