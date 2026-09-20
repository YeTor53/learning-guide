"""转写接口（r010 路径 B；路由薄壳：取依赖 → 调 service → 信封）。

设计事实源：`docs/rounds/r010-transcription/design.md` §2.5；决定见 ADR-0022。
只有两条：上传一段（multipart）与按房间读（列表）。三源合一的 `/conversation` 在 cp-2 落。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from psycopg import Connection

from app.api.deps import current_user, db_conn
from app.api.envelope import ok
from app.api.errors import ERR_VALIDATION, AppError
from app.config import load_settings
from app.schemas.auth import UserVO
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
