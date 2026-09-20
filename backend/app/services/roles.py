"""角色工具（r012）：超管判据的唯一入口。

设计事实源：docs/rounds/r012-superadmin-console/design.md §2.1。
约定：其它模块禁止直接比较 `"superadmin"` 字符串——统一走这里，后续加角色只改一处。
"""
from __future__ import annotations

from typing import Optional

from app.api.errors import ERR_FORBIDDEN, ERR_UNAUTHORIZED, AppError
from app.schemas.auth import UserVO

USER = "user"
SUPERADMIN = "superadmin"
VALID_ROLES = (USER, SUPERADMIN)


def is_superadmin(actor: Optional[UserVO]) -> bool:
    """是否超管（None 一律 False）。"""
    return actor is not None and getattr(actor, "role", None) == SUPERADMIN


def assert_superadmin(actor: Optional[UserVO]) -> UserVO:
    """管理后台用：未登录 → 401 `UNAUTHORIZED`；非超管 → 403 `FORBIDDEN`。"""
    if actor is None:
        raise AppError(ERR_UNAUTHORIZED, "请先登录", status=401)
    if not is_superadmin(actor):
        raise AppError(ERR_FORBIDDEN, "你没有该操作的权限", status=403)
    return actor
