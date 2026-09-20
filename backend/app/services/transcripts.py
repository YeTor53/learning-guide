"""转写片段（r010）：两条落地路径。
- **A 路径（本轮启用，ADR-0023）**：Agents worker 识别 → 前端回传最终稿文本段 → `ingest_segment` 落库（幂等键 = 官方 segment.id）；
- **B 路径（保留不激活）**：本端上传音频 → `transcribe_segment` 调 STT 落库（幂等键 = 分段序号）。

两条路径共用同一张表与同一套可见性规则；都只落最终稿（中间稿不落库）。

设计事实源：`docs/rounds/r010-transcription/design.md` §2.4；决定见 ADR-0022；需求 `docs/00-requirements/r010-transcription.md`（R6 隐私）。
口径：
- 说话人恒为**本人**（本端麦克风采集，无跨端归属问题）；
- 重传同段（同 `segment_index`）→ 幂等，不新增行、也不重复调用 STT（省钱）；
- 房间结束后不可再传（409 `ROOM_ENDED`），但已落转写**只读可查**；
- 音频不落盘：`audio` bytes 只在本次调用内使用。
"""
from __future__ import annotations

import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Any, Optional

from psycopg import Connection

from app.api.errors import (
    ERR_FORBIDDEN,
    ERR_UNAUTHORIZED,
    ERR_ROOM_ENDED,
    ERR_STT_FAILED,
    ERR_STT_NOT_CONFIGURED,
    ERR_VALIDATION,
    AppError,
)
from app.config import load_settings
from app.repositories import room_extras as extras_repo
from app.repositories import rooms as rooms_repo
from app.repositories import transcripts as repo
from app.repositories.transcripts import NewTranscript
from app.schemas.auth import UserVO
from app.schemas.transcripts import TranscriptVO
from app.security.ids import new_id
from app.services import rooms as rooms_service
from app.services import stt as stt_service

logger = logging.getLogger(__name__)

TRANSCRIPT_LIMIT_DEFAULT = 200
TRANSCRIPT_LIMIT_MAX = 200
CONVERSATION_LIMIT_DEFAULT = 200
CONVERSATION_LIMIT_MAX = 200
SEGMENT_TEXT_MAX_CHARS = 2000   # 单段文本上限（前端回传；超长即 400，防脏数据）
AGENT_PROVIDER = "livekit"       # A 路径记为房间侧识别


def _vo(item: repo.TranscriptRowWithName) -> TranscriptVO:
    row = item.transcript
    return TranscriptVO(
        id=row.id,
        room_id=row.room_id,
        speaker_id=row.speaker_id,
        speaker_name=item.display_name,
        segment_index=row.segment_index,
        external_id=row.external_id,
        text=row.text,
        language=row.language,
        started_at=row.started_at,
        duration_ms=row.duration_ms,
        final=row.final,
        provider=row.provider,
        model=row.model,
        created_at=row.created_at,
    )


def _guard_upload(conn: Connection, actor: Optional[UserVO], room_id: str) -> None:
    """上传前置：未登录 401 → 房间不存在 404 → 已结束 409 → 非活跃成员 403（锁房行防竞态）。"""
    rooms_repo.lock_room(conn, room_id)
    if actor is None:
        raise AppError(ERR_UNAUTHORIZED, "请先登录", status=401)
    item = rooms_service.assert_room_exists(conn, room_id)
    rooms_service.assert_room_active(item.room)
    if rooms_repo.get_active_member(conn, room_id, actor.id) is None:
        raise AppError(ERR_FORBIDDEN, "你不在该房间中（或已被移出）", status=403)


def _validate_segment(*, audio: bytes, segment_index: int, duration_ms: int, settings) -> None:
    if segment_index < 0:
        raise AppError(ERR_VALIDATION, "segmentIndex 不能为负", status=400)
    if not audio:
        raise AppError(ERR_VALIDATION, "音频为空", status=400)
    if len(audio) > settings.stt_max_bytes:
        raise AppError(
            ERR_VALIDATION,
            f"单段音频过大（上限 {settings.stt_max_bytes // (1024 * 1024)}MB）",
            status=400,
        )
    if duration_ms <= 0:
        raise AppError(ERR_VALIDATION, "durationMs 必须为正整数", status=400)
    if duration_ms > settings.stt_max_seconds * 1000:
        raise AppError(
            ERR_VALIDATION, f"单段时长上限 {settings.stt_max_seconds} 秒", status=400
        )


def transcribe_segment(
    conn: Connection,
    actor: Optional[UserVO],
    room_id: str,
    *,
    audio: bytes,
    filename: str,
    segment_index: int,
    started_at: datetime,
    duration_ms: int,
    language: Optional[str] = None,
    client: Optional[stt_service.SttClient] = None,
) -> TranscriptVO:
    """把一段音频转成文字并落库（幂等）。

    - 同（房间, 本人, 段号）已存在 → 直接返回已存在的那条（不重复调 STT）；
    - 未配置 STT → 503 `STT_NOT_CONFIGURED`（**不落库**）；
    - STT 失败/空文本 → 502 `STT_FAILED`（**不落库**，客户端丢段继续）。
    """
    settings = load_settings()
    with conn.transaction():
        _guard_upload(conn, actor, room_id)
    _validate_segment(audio=audio, segment_index=segment_index, duration_ms=duration_ms, settings=settings)

    existing = repo.get_by_segment(conn, room_id, actor.id, segment_index)
    if existing is not None:
        return _vo(existing)

    configured, _model = stt_service.stt_available(settings)
    if not configured:
        raise AppError(
            ERR_STT_NOT_CONFIGURED, "本房间未开启转写（服务端未配置 STT）", status=503
        )

    try:
        result = stt_service.call_stt(
            audio, filename=filename, language=language, client=client, settings=settings
        )
    except stt_service.SttNotConfigured as exc:
        raise AppError(ERR_STT_NOT_CONFIGURED, f"未配置转写服务：{exc}", status=503) from exc
    except stt_service.SttError as exc:
        raise AppError(ERR_STT_FAILED, f"转写失败：{exc}", status=502) from exc

    text = (result.text or "").strip()
    if not text:
        raise AppError(ERR_STT_FAILED, "转写失败：返回空文本", status=502)

    with conn.transaction():
        repo.insert_transcript(
            conn,
            NewTranscript(
                id=new_id("trs"),
                room_id=room_id,
                speaker_id=actor.id,
                segment_index=segment_index,
                text=text,
                language=(result.language or language or "zh"),
                started_at=started_at,
                duration_ms=duration_ms,
                provider=result.provider,
                model=result.model,
            ),
        )
    row = repo.get_by_segment(conn, room_id, actor.id, segment_index)
    if row is None:
        raise AppError("INTERNAL", "写入后读不到转写段", status=500)
    return _vo(row)


def ingest_segment(
    conn: Connection,
    actor: Optional[UserVO],
    room_id: str,
    *,
    external_id: str,
    speaker_identity: str,
    text: str,
    started_at: datetime,
    duration_ms: int = 0,
    language: str = "zh",
) -> tuple[TranscriptVO, bool]:
    """A 路径：落一段**最终稿**（前端回传）。

    - 权限：`actor` 必须是本房**活跃成员**（与上传口径一致：未登录 401 → 404 → 409 → 403）；
    - `speaker_identity` 必须**也是本房成员**（含已离开）——防止把外人写进房间记录；本项目身份＝`user_id`；
    - 幂等：`(room_id, external_id)` 命中即返回已存在的那行（`created=False`）——**谁先到谁落**，多端冗余上报安全；
    - `duration_ms` 允许为 0（真 STT 的 startTime/endTime 可能缺省），落库前兜底为 1（表约束要求 > 0）。
    """
    settings = load_settings()
    with conn.transaction():
        _guard_upload(conn, actor, room_id)
        if not external_id or len(external_id) > 128:
            raise AppError(ERR_VALIDATION, "externalId 不合法", status=400)
        members = rooms_service.list_members_for_visibility(conn, room_id)
        if speaker_identity not in members:
            raise AppError(ERR_VALIDATION, "说话人不是本房间成员", status=400)
        body = (text or "").strip()
        if not body:
            raise AppError(ERR_VALIDATION, "转写文本为空", status=400)
        if len(body) > SEGMENT_TEXT_MAX_CHARS:
            raise AppError(ERR_VALIDATION, f"单段文本上限 {SEGMENT_TEXT_MAX_CHARS} 字", status=400)

        existing = repo.get_by_external_id(conn, room_id, external_id)
        if existing is not None:
            return _vo(existing), False

        repo.insert_transcript(
            conn,
            NewTranscript(
                id=new_id("trs"),
                room_id=room_id,
                speaker_id=speaker_identity,
                text=body,
                language=(language or "zh"),
                started_at=started_at,
                duration_ms=max(1, int(duration_ms or 0)),
                provider=AGENT_PROVIDER,
                model=settings.stt_agent_name,
                external_id=external_id,
            ),
        )
    row = repo.get_by_external_id(conn, room_id, external_id)
    if row is None:
        raise AppError("INTERNAL", "写入后读不到转写段", status=500)
    return _vo(row), True


def _assert_can_read(conn: Connection, actor: Optional[UserVO], room_id: str) -> None:
    """转写/对话流的统一可见性：本房成员（含已离开）与房主/协管可读；房间可 `ended`。"""
    item = rooms_service.assert_room_exists(conn, room_id)
    try:
        rooms_service.assert_manager_role(conn, actor, item.room)
    except AppError:
        if actor is None or actor.id not in rooms_service.list_members_for_visibility(conn, room_id):
            raise AppError(ERR_FORBIDDEN, "只有这间房的成员可以查看房间记录", status=403) from None


@dataclass(frozen=True)
class ConversationItem:
    """三源合一的一条（R2/R3）：聊天 / 系统事件 / 语音转写。"""

    id: str
    kind: str                      # 'chat' | 'system' | 'speech'
    at: datetime                   # 排序键（转写用 started_at）
    speaker_id: Optional[str]
    speaker_name: Optional[str]
    text: str
    meta: dict[str, Any]           # speech: {durationMs, language, externalId}；其余为空（系统消息没有事件码列）


def build_conversation(
    conn: Connection,
    actor: Optional[UserVO],
    room_id: str,
    *,
    limit: int = CONVERSATION_LIMIT_DEFAULT,
) -> list[ConversationItem]:
    """把「聊天 + 系统消息 + 语音转写」合成一条时间正序的对话流（各取最近 `limit` 条再合并截断）。

    排序稳定键：`(at, id)`；`speech` 的 `at` 用 `started_at`（客户端给的该段音频开始时间）。
    """
    _assert_can_read(conn, actor, room_id)
    if limit < 1 or limit > CONVERSATION_LIMIT_MAX:
        raise AppError(ERR_VALIDATION, f"limit 需在 1~{CONVERSATION_LIMIT_MAX} 之间", status=400)

    items: list[ConversationItem] = []
    for found in extras_repo.list_messages(conn, room_id, None, limit):
        mid, _room_id, user_id, body, kind, created_at = found.message
        items.append(
            ConversationItem(
                id=mid,
                kind="system" if kind == "system" else "chat",
                at=created_at,
                speaker_id=user_id,
                speaker_name=found.display_name,
                text=body,
                meta={},
            )
        )
    for found in repo.list_transcripts(conn, room_id, limit=limit):
        row = found.transcript
        items.append(
            ConversationItem(
                id=row.id,
                kind="speech",
                at=row.started_at,
                speaker_id=row.speaker_id,
                speaker_name=found.display_name,
                text=row.text,
                meta={"durationMs": row.duration_ms, "language": row.language, "externalId": row.external_id},
            )
        )
    items.sort(key=lambda item: (item.at, item.id))
    return items[-limit:]


def list_transcripts(
    conn: Connection,
    actor: Optional[UserVO],
    room_id: str,
    *,
    limit: int = TRANSCRIPT_LIMIT_DEFAULT,
) -> list[TranscriptVO]:
    """按时间正序返回转写（最近 limit 条）；可见性同 `_assert_can_read`。"""
    _assert_can_read(conn, actor, room_id)
    if limit < 1 or limit > TRANSCRIPT_LIMIT_MAX:
        raise AppError(ERR_VALIDATION, f"limit 需在 1~{TRANSCRIPT_LIMIT_MAX} 之间", status=400)
    rows = repo.list_transcripts(conn, room_id, limit=limit)
    return [_vo(row) for row in reversed(rows)]
