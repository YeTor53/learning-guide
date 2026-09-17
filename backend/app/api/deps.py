"""FastAPI 依赖：数据库连接与当前用户。

设计事实源：docs/01-architecture/r001-app-architecture.md §6、§9.5；docs/02-modules/r001-rooms.md §6.7
分层：会话验签在 `security/session.py`（纯函数、无数据库），这里只做"Cookie → 用户"的装配。
"""
from __future__ import annotations

from typing import Iterator, Optional

from fastapi import Depends, Request
from psycopg import Connection

from app.api.errors import ERR_UNAUTHORIZED, AppError
from app.config import load_settings
from app.db.pool import get_conn
from app.repositories.users import get_user_by_id
from app.schemas.auth import UserVO
from app.security.session import COOKIE_NAME, read_session
from app.services.auth import to_vo


def db_conn() -> Iterator[Connection]:
    """每请求借一条连接（`with get_conn()` 保证归还；异常时回滚）。"""
    with get_conn() as conn:
        yield conn


def current_user_optional(request: Request, conn: Connection = Depends(db_conn)) -> Optional[UserVO]:
    """可选登录态：无 Cookie / 验签失败 / 用户已不存在都返回 None（不报错）。"""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    uid = read_session(token, load_settings().session_secret)
    if not uid:
        return None
    row = get_user_by_id(conn, uid)
    return to_vo(row) if row else None


def current_user(user: Optional[UserVO] = Depends(current_user_optional)) -> UserVO:
    """受保护接口用：未登录抛 401 `UNAUTHORIZED`。"""
    if user is None:
        raise AppError(ERR_UNAUTHORIZED, "请先登录", status=401)
    return user
