"""用例公共小工具（仅测试使用）。

放在独立模块里避免 conftest 与各用例文件互相 import；不做任何生产逻辑。
"""
from __future__ import annotations

import time
from uuid import uuid4

from psycopg import Connection

from app.schemas.auth import RegisterIn
from app.services import auth as auth_service

PASSWORD = "demo-pass-123"


def new_email() -> str:
    return f"u{uuid4().hex[:10]}@example.com"


def register_user(conn: Connection, display_name: str = "测试同学"):
    """直接走服务层建用户（用例里不关心注册接口本身）。"""
    return auth_service.register(conn, RegisterIn(email=new_email(), display_name=display_name, password=PASSWORD))


def session_cookie(user_id: str) -> tuple[str, str]:
    """返回 (cookie 名, cookie 值) 供 TestClient 使用。"""
    from app.config import load_settings
    from app.security.session import COOKIE_NAME, sign_session

    return COOKIE_NAME, sign_session(user_id, int(time.time()) + 300, load_settings().session_secret)
