"""转写接口（r010；路由薄壳：取依赖 → 调 service → 信封）。

设计事实源：`docs/rounds/r010-transcription/design.md` §2.5（B 路径）与 §9.3.4（A 路径）；决定见 ADR-0023。
- A 路径（本轮启用）：`POST /rooms/{id}/transcripts/segments`（前端回传最终稿文本）+ `GET /stt/status`；
- B 路径（保留不激活）：`POST /rooms/{id}/transcripts`（音频 multipart，`STT_MODE=backend` 时才有意义）。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile
from psycopg import Connection

from app.api.deps import current_user, db_conn
from app.api.envelope import ok
from app.api.errors import ERR_VALIDATION, AppError
from app.config import load_settings
from app.schemas.auth import UserVO
from app.schemas.transcripts import ConversationItemVO, SegmentIn
from app.services import transcripts as transcripts_service

router = APIRouter(tags=["transcripts"])


def _dump(model) -> dict:
    """VO → JSON 字典（camelCase，时间转 ISO 串）。"""
    return model.model_dump(mode="json", by_alias=True)


def parse_started_at(raw: str) -> datetime:
    """把客户端给的 ISO 时间转成带时区的 datetime（无时区按 UTC 解释）。

    客户端时钟与服务器可能不同，这里只做格式与合法性校验，不做「未来时间」判定。
    """
    text = (raw or "").strip().replace("Z", "+00:00")
    try:
        value = datetime.fromisoformat(text)
    except ValueError as exc:
        raise AppError(ERR_VALIDATION, "startedAt 需为 ISO 时间（如 2026-09-20T10:00:00Z）", status=400) from exc
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


@router.post("/rooms/{room_id}/transcripts", status_code=201)
async def upload_transcript(
    room_id: str,
    file: UploadFile = File(..., description="一段音频（webm/wav/mp3 等，≤ 单段上限）"),
    segment_index: int = Form(..., alias="segmentIndex"),
    started_at: str = Form(..., alias="startedAt"),
    duration_ms: int = Form(..., alias="durationMs"),
    language: Optional[str] = Form(None),
    actor: UserVO = Depends(current_user),
    conn: Connection = Depends(db_conn),
):
    """上传一段音频 → 转写 → 落库（幂等）。未配置 503 / 失败 502 / 超限 400 / 已结束 409。"""
    settings = load_settings()
    # 多读 1 字节用于判超限；音频只在本请求内存在，不落盘
    data = await file.read(settings.stt_max_bytes + 1)
    item = transcripts_service.transcribe_segment(
        conn,
        actor,
        room_id,
        audio=data,
        filename=file.filename or "segment.webm",
        segment_index=segment_index,
        started_at=parse_started_at(started_at),
        duration_ms=duration_ms,
        language=language,
    )
    return ok(_dump(item), status=201)


@router.post("/rooms/{room_id}/transcripts/segments", status_code=201)
def ingest_segment(
    room_id: str,
    payload: SegmentIn,
    actor: UserVO = Depends(current_user),
    conn: Connection = Depends(db_conn),
):
    """A 路径：接收前端回传的转写段。

    - `final=false`（中间稿）→ **204 且不落库**（只落最终稿，ADR-0022 D3）；
    - `final=true` → 201 `{transcript, created}`；同 `externalId` 重复上报 → `created=false`（幂等）。
    """
    if not payload.final:
        return Response(status_code=204)
    item, created = transcripts_service.ingest_segment(
        conn,
        actor,
        room_id,
        external_id=payload.external_id,
        speaker_identity=payload.speaker_identity,
        text=payload.text,
        started_at=payload.started_at,
        duration_ms=payload.duration_ms,
        language=payload.language,
    )
    return ok({"transcript": _dump(item), "created": created}, status=201)


@router.get("/stt/status", status_code=200)
def read_stt_status(
    actor: UserVO = Depends(current_user),
):
    """转写配置状态（前端据此显示"转写：开启/未开启"，不报错、不伪装）。"""
    settings = load_settings()
    return ok(
        {
            "mode": settings.stt_mode,
            "agentName": settings.stt_agent_name,
            "maxSessions": settings.stt_max_sessions,
            "segmentSeconds": settings.stt_segment_seconds,
        },
        status=200,
    )


@router.get("/rooms/{room_id}/conversation", status_code=200)
def read_conversation(
    room_id: str,
    limit: int = Query(transcripts_service.CONVERSATION_LIMIT_DEFAULT, ge=1),
    actor: UserVO = Depends(current_user),
    conn: Connection = Depends(db_conn),
):
    """三源合一对话流（聊天 + 系统事件 + 语音转写），时间正序；可见性同转写。"""
    items = transcripts_service.build_conversation(conn, actor, room_id, limit=limit)
    payload = [
        ConversationItemVO(
            id=item.id,
            kind=item.kind,
            at=item.at,
            speaker_id=item.speaker_id,
            speaker_name=item.speaker_name,
            text=item.text,
            meta=item.meta,
        )
        for item in items
    ]
    return ok({"items": [_dump(item) for item in payload]}, status=200)


@router.get("/rooms/{room_id}/transcripts", status_code=200)
def read_transcripts(
    room_id: str,
    limit: int = Query(transcripts_service.TRANSCRIPT_LIMIT_DEFAULT, ge=1),
    actor: UserVO = Depends(current_user),
    conn: Connection = Depends(db_conn),
):
    """按时间正序读该房转写（本房成员，含已离开；房间结束后仍可读）。"""
    items = transcripts_service.list_transcripts(conn, actor, room_id, limit=limit)
    return ok({"transcripts": [_dump(item) for item in items]}, status=200)
