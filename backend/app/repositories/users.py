"""`users` 表的参数化 SQL 绑定（不写业务判断、不开事务）。

设计事实源：docs/01-architecture/r001-app-architecture.md §3（分层）、§9.4；表定义见模块页 §3
行映射：统一返回 `UserRow` dataclass，不把驱动元组漏到上层。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from psycopg import Connection

_COLUMNS = "id, email, display_name, password_hash, created_at"


@dataclass(frozen=True)
class UserRow:
    id: str
    email: str
    display_name: str
    password_hash: str
    created_at: datetime


def _to_row(row: tuple) -> UserRow:
    return UserRow(id=row[0], email=row[1], display_name=row[2], password_hash=row[3], created_at=row[4])


def insert_user(conn: Connection, user_id: str, email: str, display_name: str, password_hash: str) -> None:
    conn.execute(
        "INSERT INTO users (id, email, display_name, password_hash) VALUES (%s, %s, %s, %s)",
        (user_id, email, display_name, password_hash),
    )


def get_user_by_id(conn: Connection, user_id: str) -> Optional[UserRow]:
    row = conn.execute(f"SELECT {_COLUMNS} FROM users WHERE id = %s", (user_id,)).fetchone()
    return _to_row(row) if row else None


def get_user_by_email(conn: Connection, email: str) -> Optional[UserRow]:
    """按邮箱查（大小写不敏感，与唯一索引 `ux_users_email_lower` 同口径）。"""
    row = conn.execute(f"SELECT {_COLUMNS} FROM users WHERE lower(email) = lower(%s)", (email,)).fetchone()
    return _to_row(row) if row else None
