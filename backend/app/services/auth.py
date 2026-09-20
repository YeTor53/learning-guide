"""账户业务规则（唯一写库入口；事务边界在本层）。

设计事实源：docs/01-architecture/r001-app-architecture.md §6（会话）、§8（错误码）、§13（失败与边界）
规则：重复邮箱 → 409 `EMAIL_TAKEN`；口令错误与邮箱不存在都返回 401 `INVALID_CREDENTIALS`（不区分，防枚举）。
"""
from __future__ import annotations

from typing import Optional

from psycopg import Connection
from psycopg.errors import UniqueViolation

from app.api.errors import ERR_EMAIL_TAKEN, ERR_INVALID_CREDENTIALS, AppError
from app.repositories.users import UserRow, get_user_by_email, get_user_by_id, insert_user
from app.schemas.auth import LoginIn, RegisterIn, UserVO
from app.security.ids import new_id
from app.security.password import dummy_verify, hash_password, verify_password

INVALID_CREDENTIALS_MESSAGE = "邮箱或密码不正确"
EMAIL_TAKEN_MESSAGE = "该邮箱已注册"


def to_vo(row: UserRow) -> UserVO:
    """库行 → VO（唯一转换点，避免 `password_hash` 意外外泄）。"""
    return UserVO(
        id=row.id, email=row.email, display_name=row.display_name, role=row.role, created_at=row.created_at
    )


def register(conn: Connection, data: RegisterIn) -> UserVO:
    """注册：邮箱唯一（先查后插，并捕获唯一索引冲突兜底并发）。"""
    try:
        with conn.transaction():
            if get_user_by_email(conn, data.email) is not None:
                raise AppError(ERR_EMAIL_TAKEN, EMAIL_TAKEN_MESSAGE, status=409)
            user_id = new_id("usr")
            insert_user(conn, user_id, data.email, data.display_name, hash_password(data.password))
    except UniqueViolation as exc:  # 并发注册同一邮箱
        raise AppError(ERR_EMAIL_TAKEN, EMAIL_TAKEN_MESSAGE, status=409) from exc
    row = get_user_by_id(conn, user_id)
    if row is None:  # 理论上不可能：同一连接读自己刚提交的行
        raise AppError("INTERNAL", "注册后无法读取用户", status=500)
    return to_vo(row)


def login(conn: Connection, data: LoginIn) -> UserVO:
    """登录：不区分"邮箱不存在"与"口令错误"，都不泄露账号是否存在。"""
    row = get_user_by_email(conn, data.email)
    if row is None:
        dummy_verify(data.password)
        raise AppError(ERR_INVALID_CREDENTIALS, INVALID_CREDENTIALS_MESSAGE, status=401)
    if not verify_password(data.password, row.password_hash):
        raise AppError(ERR_INVALID_CREDENTIALS, INVALID_CREDENTIALS_MESSAGE, status=401)
    return to_vo(row)


def get_user(conn: Connection, user_id: str) -> Optional[UserVO]:
    """按 id 取用户（会话 Cookie 解出的 `uid` → 当前用户）。"""
    row = get_user_by_id(conn, user_id)
    return to_vo(row) if row else None
