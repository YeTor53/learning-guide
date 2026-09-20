"""`users` 表的参数化 SQL 绑定（不写业务判断、不开事务）。

设计事实源：docs/01-architecture/r001-app-architecture.md §3（分层）、§9.4；表定义见模块页 §3
行映射：统一返回 `UserRow` dataclass，不把驱动元组漏到上层。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from psycopg import Connection

_COLUMNS = "id, email, display_name, password_hash, role, last_seen_at, created_at"


@dataclass(frozen=True)
class UserRow:
    id: str
    email: str
    display_name: str
    password_hash: str
    role: str                # r012：'user' | 'superadmin'
    last_seen_at: Optional[datetime]   # r012：最后一次心跳（POST /api/presence）
    created_at: datetime


def _to_row(row: tuple) -> UserRow:
    return UserRow(
        id=row[0], email=row[1], display_name=row[2], password_hash=row[3],
        role=row[4], last_seen_at=row[5], created_at=row[6],
    )


def insert_user(
    conn: Connection,
    user_id: str,
    email: str,
    display_name: str,
    password_hash: str,
    role: str = "user",
) -> None:
    """注册路径不传 role（默认 'user'）；seed / 提权脚本才写 'superadmin'。"""
    conn.execute(
        "INSERT INTO users (id, email, display_name, password_hash, role) VALUES (%s, %s, %s, %s, %s)",
        (user_id, email, display_name, password_hash, role),
    )


def get_user_by_id(conn: Connection, user_id: str) -> Optional[UserRow]:
    row = conn.execute(f"SELECT {_COLUMNS} FROM users WHERE id = %s", (user_id,)).fetchone()
    return _to_row(row) if row else None


def touch_last_seen(conn: Connection, user_id: str, at: datetime) -> None:
    """写一次心跳（r012 `POST /api/presence`）；只改 `last_seen_at` 一列。"""
    conn.execute("UPDATE users SET last_seen_at = %s WHERE id = %s", (at, user_id))


def set_user_role(conn: Connection, user_id: str, role: str) -> int:
    """改角色（`grant_superadmin.py` 用）；返回影响行数（0 = 用户不存在）。"""
    cursor = conn.execute("UPDATE users SET role = %s WHERE id = %s", (role, user_id))
    return cursor.rowcount


def list_online_user_ids(conn: Connection, since: datetime) -> set[str]:
    """最近心跳不早于 `since` 的用户 id 集合（在线口径，r012 §2.6）。"""
    rows = conn.execute(
        "SELECT id FROM users WHERE last_seen_at IS NOT NULL AND last_seen_at >= %s", (since,)
    ).fetchall()
    return {row[0] for row in rows}


def get_user_by_email(conn: Connection, email: str) -> Optional[UserRow]:
    """按邮箱查（大小写不敏感，与唯一索引 `ux_users_email_lower` 同口径）。"""
    row = conn.execute(f"SELECT {_COLUMNS} FROM users WHERE lower(email) = lower(%s)", (email,)).fetchone()
    return _to_row(row) if row else None
