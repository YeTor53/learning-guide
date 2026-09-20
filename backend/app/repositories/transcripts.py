"""`transcripts` 的参数化 SQL（r010）。

设计事实源：`docs/rounds/r010-transcription/design.md` §2.2；决定见 ADR-0022。
纪律：与其它 repository 同层——只做 SQL 与行映射，不写业务判断、不开事务。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from psycopg import Connection

TRANSCRIPT_FIELDS = (
    "id", "room_id", "speaker_id", "segment_index", "text", "language",
    "started_at", "duration_ms", "final", "provider", "model", "created_at",
)


@dataclass(frozen=True)
class NewTranscript:
    """待落库的转写段（`segment_index` + 说话人 + 房间构成幂等键）。"""

    id: str
    room_id: str
    speaker_id: str
    segment_index: int
    text: str
    language: str
    started_at: datetime
    duration_ms: int
    provider: str = ""
    model: str = ""


@dataclass(frozen=True)
class TranscriptRow:
    id: str
    room_id: str
    speaker_id: str
    segment_index: int
    text: str
    language: str
    started_at: datetime
    duration_ms: int
    final: bool
    provider: str
    model: str
    created_at: datetime


@dataclass(frozen=True)
class TranscriptRowWithName:
    """转写行 + 说话人显示名（列表与三源合一共用）。"""

    transcript: TranscriptRow
    display_name: str


def insert_transcript(conn: Connection, row: NewTranscript) -> bool:
    """插入一段转写；同（房间, 说话人, 段号）已存在则**什么都不做**并返回 False（幂等）。"""
    cur = conn.execute(
        """INSERT INTO transcripts
             (id, room_id, speaker_id, segment_index, text, language, started_at, duration_ms, provider, model)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (room_id, speaker_id, segment_index) DO NOTHING""",
        (
            row.id, row.room_id, row.speaker_id, row.segment_index, row.text, row.language,
            row.started_at, row.duration_ms, row.provider, row.model,
        ),
    )
    return cur.rowcount == 1


def get_by_segment(
    conn: Connection, room_id: str, speaker_id: str, segment_index: int
) -> TranscriptRowWithName | None:
    """按幂等键取一条（重传时把已存在的那条还回去）。"""
    cur = conn.execute(
        f"""SELECT {", ".join("t." + f for f in TRANSCRIPT_FIELDS)}, u.display_name
             FROM transcripts t JOIN users u ON u.id = t.speaker_id
            WHERE t.room_id = %s AND t.speaker_id = %s AND t.segment_index = %s""",
        (room_id, speaker_id, segment_index),
    )
    found = cur.fetchone()
    return TranscriptRowWithName(TranscriptRow(*found[: len(TRANSCRIPT_FIELDS)]), found[len(TRANSCRIPT_FIELDS)]) if found else None


def list_transcripts(conn: Connection, room_id: str, *, limit: int = 200) -> list[TranscriptRowWithName]:
    """取该房**最近** limit 条（按 `started_at`/`id` 倒序取，调用方负责翻正）。"""
    cur = conn.execute(
        f"""SELECT {", ".join("t." + f for f in TRANSCRIPT_FIELDS)}, u.display_name
             FROM transcripts t JOIN users u ON u.id = t.speaker_id
            WHERE t.room_id = %s
            ORDER BY t.started_at DESC, t.id DESC
            LIMIT %s""",
        (room_id, limit),
    )
    return [TranscriptRowWithName(TranscriptRow(*row[: len(TRANSCRIPT_FIELDS)]), row[len(TRANSCRIPT_FIELDS)]) for row in cur.fetchall()]


def list_since(conn: Connection, room_id: str, *, limit: int = 200) -> list[TranscriptRowWithName]:
    """同 `list_transcripts`，语义别名（三源合一用；保留显式入口便于将来加时间窗）。"""
    return list_transcripts(conn, room_id, limit=limit)


def count_speakers(conn: Connection, room_id: str) -> int:
    """说过话的人数（转写页/纪要素材的概览用）。"""
    return conn.execute("SELECT count(DISTINCT speaker_id) FROM transcripts WHERE room_id = %s", (room_id,)).fetchone()[0]
