"""`transcripts` 的参数化 SQL（r010）。

设计事实源：`docs/rounds/r010-transcription/design.md` §2.2（B 路径）与 §9.3.2（A 路径换轨）；决定见 ADR-0023。
纪律：与其它 repository 同层——只做 SQL 与行映射，不写业务判断、不开事务。
幂等键（两条路径各一）：B 路径 `(room_id, speaker_id, segment_index)`；A 路径 `(room_id, external_id)`（= 官方 segment.id）。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from psycopg import Connection

TRANSCRIPT_FIELDS = (
    "id", "room_id", "speaker_id", "segment_index", "text", "language",
    "started_at", "duration_ms", "final", "provider", "model", "created_at", "external_id",
)


@dataclass(frozen=True)
class NewTranscript:
    """待落库的转写段。

    - B 路径（本端上传音频）：填 `segment_index`，`external_id=None`；
    - A 路径（worker 识别 + 前端回传）：填 `external_id`（官方 segment.id），`segment_index=None`。
    """

    id: str
    room_id: str
    speaker_id: str
    text: str
    language: str
    started_at: datetime
    duration_ms: int
    segment_index: Optional[int] = None
    provider: str = ""
    model: str = ""
    external_id: Optional[str] = None


@dataclass(frozen=True)
class TranscriptRow:
    id: str
    room_id: str
    speaker_id: str
    segment_index: Optional[int]
    text: str
    language: str
    started_at: datetime
    duration_ms: int
    final: bool
    provider: str
    model: str
    created_at: datetime
    external_id: Optional[str]


@dataclass(frozen=True)
class TranscriptRowWithName:
    """转写行 + 说话人显示名（列表与三源合一共用）。"""

    transcript: TranscriptRow
    display_name: str


def _with_name(row: tuple) -> TranscriptRowWithName:
    return TranscriptRowWithName(TranscriptRow(*row[: len(TRANSCRIPT_FIELDS)]), row[len(TRANSCRIPT_FIELDS)])


def insert_transcript(conn: Connection, row: NewTranscript) -> bool:
    """插入一段转写；命中幂等键则**什么都不做**并返回 False。

    - 有 `external_id` → 冲突目标 `(room_id, external_id)`（A 路径，多端冗余上报安全）；
    - 否则 → 冲突目标 `(room_id, speaker_id, segment_index)`（B 路径，重传同段安全）。
    """
    if row.external_id:
        cur = conn.execute(
            """INSERT INTO transcripts
                 (id, room_id, speaker_id, segment_index, text, language, started_at, duration_ms,
                  provider, model, external_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (room_id, external_id) DO NOTHING""",
            (
                row.id, row.room_id, row.speaker_id, row.segment_index, row.text, row.language,
                row.started_at, row.duration_ms, row.provider, row.model, row.external_id,
            ),
        )
    else:
        cur = conn.execute(
            """INSERT INTO transcripts
                 (id, room_id, speaker_id, segment_index, text, language, started_at, duration_ms,
                  provider, model, external_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (room_id, speaker_id, segment_index) DO NOTHING""",
            (
                row.id, row.room_id, row.speaker_id, row.segment_index, row.text, row.language,
                row.started_at, row.duration_ms, row.provider, row.model, row.external_id,
            ),
        )
    return cur.rowcount == 1


def get_by_external_id(conn: Connection, room_id: str, external_id: str) -> Optional[TranscriptRowWithName]:
    """按官方 segment id 取一条（A 路径幂等：重复上报把已存在的那条还回去）。"""
    cur = conn.execute(
        f"""SELECT {", ".join("t." + f for f in TRANSCRIPT_FIELDS)}, u.display_name
             FROM transcripts t JOIN users u ON u.id = t.speaker_id
            WHERE t.room_id = %s AND t.external_id = %s""",
        (room_id, external_id),
    )
    found = cur.fetchone()
    return _with_name(found) if found else None


def get_by_segment(
    conn: Connection, room_id: str, speaker_id: str, segment_index: int
) -> Optional[TranscriptRowWithName]:
    """按 B 路径幂等键取一条。"""
    cur = conn.execute(
        f"""SELECT {", ".join("t." + f for f in TRANSCRIPT_FIELDS)}, u.display_name
             FROM transcripts t JOIN users u ON u.id = t.speaker_id
            WHERE t.room_id = %s AND t.speaker_id = %s AND t.segment_index = %s""",
        (room_id, speaker_id, segment_index),
    )
    found = cur.fetchone()
    return _with_name(found) if found else None


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
    return [_with_name(row) for row in cur.fetchall()]


def count_speakers(conn: Connection, room_id: str) -> int:
    """说过话的人数（概览用）。"""
    return conn.execute("SELECT count(DISTINCT speaker_id) FROM transcripts WHERE room_id = %s", (room_id,)).fetchone()[0]
