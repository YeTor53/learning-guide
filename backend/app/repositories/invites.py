"""`invites` 的参数化 SQL（r008）。

设计事实源：`docs/rounds/r008-assignment-gaps/design.md` §2.4；决定见 ADR-0019。
纪律：只做 SQL 与行映射；锁（`FOR UPDATE`）由 service 在事务里调用。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from psycopg import Connection

INVITE_FIELDS = ("id", "room_id", "code", "created_by", "expires_at", "max_uses", "used_count", "created_at")


@dataclass(frozen=True)
class NewInvite:
    id: str
    room_id: str
    code: str
    created_by: str
    expires_at: datetime
    max_uses: int


@dataclass(frozen=True)
class InviteRow:
    id: str
    room_id: str
    code: str
    created_by: Optional[str]
    expires_at: datetime
    max_uses: int
    used_count: int
    created_at: datetime


def insert_invite(conn: Connection, row: NewInvite) -> None:
    conn.execute(
        """INSERT INTO invites (id, room_id, code, created_by, expires_at, max_uses, used_count)
           VALUES (%s, %s, %s, %s, %s, %s, 0)""",
        (row.id, row.room_id, row.code, row.created_by, row.expires_at, row.max_uses),
    )


def get_invite_by_code(conn: Connection, code: str, *, lock: bool = False) -> Optional[InviteRow]:
    """按码取邀请；`lock=True` 时 `FOR UPDATE`（调用方必须在事务内）。"""
    suffix = " FOR UPDATE" if lock else ""
    cur = conn.execute(
        f"SELECT {', '.join(INVITE_FIELDS)} FROM invites WHERE lower(code) = lower(%s){suffix}",
        (code,),
    )
    row = cur.fetchone()
    return InviteRow(*row) if row else None


def bump_invite_used(conn: Connection, invite_id: str) -> int:
    """`used_count += 1`；返回影响行数。"""
    cur = conn.execute("UPDATE invites SET used_count = used_count + 1 WHERE id = %s", (invite_id,))
    return cur.rowcount


def list_invites(conn: Connection, room_id: str) -> list[InviteRow]:
    cur = conn.execute(
        f"SELECT {', '.join(INVITE_FIELDS)} FROM invites WHERE room_id = %s ORDER BY created_at DESC LIMIT 20",
        (room_id,),
    )
    return [InviteRow(*row) for row in cur.fetchall()]
