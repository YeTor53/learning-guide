"""`session_summaries` 的参数化 SQL（r008）。

设计事实源：`docs/rounds/r008-assignment-gaps/design.md` §2.3
纪律：与其它 repository 同层——只做 SQL 与行映射，不写业务判断、不开事务。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from psycopg import Connection

SUMMARY_FIELDS = (
    "id", "room_id", "status", "provider", "model",
    "input_digest", "content", "error", "created_by", "created_at", "updated_at",
)


@dataclass(frozen=True)
class NewSummary:
    id: str
    room_id: str
    status: str
    provider: str
    model: str
    input_digest: str
    content: str
    error: Optional[str]
    created_by: Optional[str]


@dataclass(frozen=True)
class SummaryRow:
    id: str
    room_id: str
    status: str
    provider: str
    model: str
    input_digest: str
    content: str
    error: Optional[str]
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime


def upsert_summary(conn: Connection, row: NewSummary) -> None:
    """按 `room_id` 覆盖写（唯一索引保证一间房一行）；`created_at` 保留首次。"""
    conn.execute(
        """INSERT INTO session_summaries
             (id, room_id, status, provider, model, input_digest, content, error, created_by)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (room_id) DO UPDATE SET
             status = EXCLUDED.status,
             provider = EXCLUDED.provider,
             model = EXCLUDED.model,
             input_digest = EXCLUDED.input_digest,
             content = EXCLUDED.content,
             error = EXCLUDED.error,
             updated_at = clock_timestamp()""",
        (
            row.id, row.room_id, row.status, row.provider, row.model,
            row.input_digest, row.content, row.error, row.created_by,
        ),
    )


def get_summary(conn: Connection, room_id: str) -> Optional[SummaryRow]:
    """按房间取纪要（未生成返回 None）。"""
    cur = conn.execute(
        f"SELECT {', '.join(SUMMARY_FIELDS)} FROM session_summaries WHERE room_id = %s",
        (room_id,),
    )
    found = cur.fetchone()
    return SummaryRow(*found) if found else None
