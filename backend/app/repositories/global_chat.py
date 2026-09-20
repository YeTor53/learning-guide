"""`global_messages` 的读写（r012 全服大屏聊天）。

设计事实源：docs/rounds/r012-superadmin-console/design.md §4.1。
- 倒序取最近 N 条（`before_id` 做游标：取比它更早的）；
- 限流用**库计数**（重启不放大额度）；JOIN users 取显示名，避免上层再查。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from psycopg import Connection


@dataclass(frozen=True)
class NewGlobalMessage:
    id: str
    user_id: str
    body: str


@dataclass(frozen=True)
class GlobalMessageRow:
    id: str
    user_id: str
    body: str
    created_at: datetime


@dataclass(frozen=True)
class GlobalMessageRowWithName:
    message: GlobalMessageRow
    display_name: str


def insert_global_message(conn: Connection, row: NewGlobalMessage) -> None:
    conn.execute(
        "INSERT INTO global_messages (id, user_id, body) VALUES (%s, %s, %s)",
        (row.id, row.user_id, row.body),
    )


def list_global_messages(conn: Connection, limit: int, before_id: Optional[str] = None) -> list[GlobalMessageRowWithName]:
    """最近 `limit` 条（倒序）；给了 `before_id` 就只取比它更早的（翻历史用）。"""
    rows = conn.execute(
        """SELECT g.id, g.user_id, g.body, g.created_at, u.display_name
           FROM global_messages g
           JOIN users u ON u.id = g.user_id
           WHERE (%s::text IS NULL
                  OR g.created_at < (SELECT created_at FROM global_messages WHERE id = %s))
           ORDER BY g.created_at DESC, g.id DESC
           LIMIT %s""",
        (before_id, before_id, limit),
    ).fetchall()
    return [
        GlobalMessageRowWithName(
            message=GlobalMessageRow(id=row[0], user_id=row[1], body=row[2], created_at=row[3]),
            display_name=row[4],
        )
        for row in rows
    ]


def count_recent_by_user(conn: Connection, user_id: str, since: datetime) -> int:
    """该用户在窗口内已发条数（限流判据，库计数）。"""
    return conn.execute(
        "SELECT count(*) FROM global_messages WHERE user_id = %s AND created_at >= %s",
        (user_id, since),
    ).fetchone()[0]


def count_all(conn: Connection) -> int:
    return conn.execute("SELECT count(*) FROM global_messages").fetchone()[0]
