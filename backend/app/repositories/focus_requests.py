"""`focus_requests` 的参数化 SQL（r009）。

设计事实源：docs/rounds/r009-focus-system/design.md §2.2；决定见 ADR-0021 D2。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from psycopg import Connection

FIELDS = ("id", "room_id", "requester_id", "status", "decided_by", "created_at", "decided_at")


@dataclass(frozen=True)
class RequestRow:
    id: str
    room_id: str
    requester_id: str
    status: str
    decided_by: Optional[str]
    created_at: datetime
    decided_at: Optional[datetime]


@dataclass(frozen=True)
class RequestRowWithName(RequestRow):
    requester_name: str


def insert_request(conn: Connection, request_id: str, room_id: str, requester_id: str) -> Optional[RequestRow]:
    """写一条 pending；已存在 pending → 返回 None（调用方按幂等处理）。"""
    row = conn.execute(
        f"""INSERT INTO focus_requests (id, room_id, requester_id, status)
            VALUES (%s, %s, %s, 'pending')
            ON CONFLICT (room_id, requester_id) WHERE status = 'pending' DO NOTHING
            RETURNING {', '.join(FIELDS)}""",
        (request_id, room_id, requester_id),
    ).fetchone()
    return RequestRow(*row) if row else None


def get_pending(conn: Connection, room_id: str, requester_id: str, *, lock: bool = False) -> Optional[RequestRow]:
    suffix = " FOR UPDATE" if lock else ""
    row = conn.execute(
        f"""SELECT {', '.join(FIELDS)} FROM focus_requests
             WHERE room_id = %s AND requester_id = %s AND status = 'pending'{suffix}""",
        (room_id, requester_id),
    ).fetchone()
    return RequestRow(*row) if row else None


def get_by_id(conn: Connection, request_id: str, *, lock: bool = False) -> Optional[RequestRow]:
    suffix = " FOR UPDATE" if lock else ""
    row = conn.execute(
        f"SELECT {', '.join(FIELDS)} FROM focus_requests WHERE id = %s{suffix}", (request_id,)
    ).fetchone()
    return RequestRow(*row) if row else None


def list_pending(conn: Connection, room_id: str) -> list[RequestRowWithName]:
    rows = conn.execute(
        f"""SELECT r.id, r.room_id, r.requester_id, r.status, r.decided_by, r.created_at, r.decided_at, u.display_name
              FROM focus_requests r JOIN users u ON u.id = r.requester_id
             WHERE r.room_id = %s AND r.status = 'pending'
             ORDER BY r.created_at ASC, r.id ASC""",
        (room_id,),
    ).fetchall()
    return [RequestRowWithName(*row) for row in rows]


def decide(conn: Connection, request_id: str, status: str, decided_by: str) -> int:
    cur = conn.execute(
        """UPDATE focus_requests SET status = %s, decided_by = %s, decided_at = clock_timestamp()
            WHERE id = %s AND status = 'pending'""",
        (status, decided_by, request_id),
    )
    return cur.rowcount


def cancel_pending_for_user(conn: Connection, room_id: str, user_id: str) -> int:
    """焦点被清 / 人离开时收尾，避免挂着一堆永不可能批准的申请。"""
    cur = conn.execute(
        """UPDATE focus_requests SET status = 'cancelled', decided_at = clock_timestamp()
            WHERE room_id = %s AND requester_id = %s AND status = 'pending'""",
        (room_id, user_id),
    )
    return cur.rowcount
