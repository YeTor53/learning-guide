"""语音转文字（r010）：**唯一 STT 出口**。

设计事实源：`docs/rounds/r010-transcription/design.md` §2.3；决定见 ADR-0022（路径 B：本端采集 → 自有后端 → STT）。
纪律（与 `services/summary.call_llm` 同级）：
- 只读 `Settings`，不做 HTTP 之外的事，不 import 上层；
- 外部调用集中在本模块，**失败不改业务真相**（调用方决定是否落库）；
- `client` 参数可注入 → 用例全离线打桩，不打真实网络；
- 音频**不落盘**：进来的 bytes 用完即丢；日志只记字节数与耗时，**不记文本内容**。
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional

import aiohttp

from app.config import Settings, load_settings

logger = logging.getLogger(__name__)

STT_TIMEOUT_SECONDS = 60
STT_RESPONSE_FORMAT = "json"


class SttNotConfigured(Exception):
    """未配置 STT（映射 503 `STT_NOT_CONFIGURED`）。"""


class SttError(Exception):
    """STT 调用失败或返回空文本（映射 502 `STT_FAILED`）。"""


@dataclass(frozen=True)
class SttResult:
    """一段音频的转写结果（`final` 恒为 True：本轮只落最终稿）。"""

    text: str
    language: str
    provider: str
    model: str


SttClient = Callable[[bytes, str, Optional[str]], SttResult]


def _settings(settings: Optional[Settings] = None) -> Settings:
    return settings if settings is not None else load_settings()


def stt_available(settings: Optional[Settings] = None) -> tuple[bool, str]:
    """(是否已配置, 模型名)。空 base/key = 未配置 → 前端禁用开关并提示。"""
    s = _settings(settings)
    configured = bool(s.stt_base_url and s.stt_api_key)
    return configured, (s.stt_model if configured else "")


def estimate_segment_seconds(settings: Optional[Settings] = None) -> int:
    """回给前端的建议分段长度（秒）——改 `STT_SEGMENT_SECONDS` 一处即生效。"""
    return _settings(settings).stt_segment_seconds


def call_stt(
    audio: bytes,
    *,
    filename: str,
    language: Optional[str] = None,
    client: Optional[SttClient] = None,
    settings: Optional[Settings] = None,
) -> SttResult:
    """唯一 STT 出口：Whisper 兼容 `POST {STT_BASE_URL}/audio/transcriptions`（multipart）。

    未配置 → `SttNotConfigured`；网络/非 200/空文本 → `SttError`。
    `client` 注入时直接返回它的结果（用例打桩，不走网络）。
    """
    s = _settings(settings)
    if client is not None:
        return client(audio, filename, language)
    if not s.stt_base_url or not s.stt_api_key:
        raise SttNotConfigured("未配置 STT（STT_BASE_URL / STT_API_KEY）")

    url = s.stt_base_url.rstrip("/") + "/audio/transcriptions"

    async def _post() -> str:
        timeout = aiohttp.ClientTimeout(total=STT_TIMEOUT_SECONDS)
        form = aiohttp.FormData()
        form.add_field("model", s.stt_model)
        form.add_field("file", audio, filename=filename, content_type="application/octet-stream")
        form.add_field("response_format", STT_RESPONSE_FORMAT)
        if language:
            form.add_field("language", language)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                url, data=form, headers={"Authorization": f"Bearer {s.stt_api_key}"}
            ) as resp:
                if resp.status != 200:
                    body = (await resp.text())[:300]
                    raise SttError(f"STT HTTP {resp.status}: {body}")
                data = await resp.json(content_type=None)
        text = (data.get("text") or "").strip()
        if not text:
            raise SttError("STT 返回空文本")
        return text

    try:
        text = asyncio.run(_post())
    except SttError:
        raise
    except Exception as exc:  # noqa: BLE001 —— 网络/解析异常统一映射
        raise SttError(f"{type(exc).__name__}: {exc}") from exc

    # 只记规模，不记内容（隐私：转写文本不入日志）
    logger.info("STT 段完成：%d 字节 → %d 字", len(audio), len(text))
    return SttResult(text=text, language=language or "zh", provider=s.stt_base_url, model=s.stt_model)


# ---------------- r011：worker 健康上报（内存态，零迁移） ----------------

_HEARTBEATS: dict[str, dict] = {}
"""room_id → {workerId, sessions, lastSeenAt, lastError}。进程内存：后端重启即清空，**不伪装**「一直在跑」。"""

HEARTBEAT_FRESH_SECONDS = 15
"""心跳新鲜窗口（秒）：前端把这个窗口内的心跳也算「转写开启」。"""


def record_heartbeat(room_id: str, worker_id: str, sessions: int = 0, last_error: Optional[str] = None) -> None:
    """记一次 worker 心跳（由 `POST /api/stt/heartbeat` 调用）。

    `last_error`（r013）：worker 上报的最近一次错误；**带错误的心跳也刷新 `lastSeenAt`**——那说明 worker 还活着。
    """
    _HEARTBEATS[room_id] = {
        "workerId": worker_id,
        "sessions": int(sessions),
        "lastSeenAt": datetime.now(timezone.utc),
        "lastError": (last_error or None),
    }


def last_heartbeat(room_id: str) -> Optional[dict]:
    """该房最近一次心跳（无记录返回 None）。"""
    return _HEARTBEATS.get(room_id)


def heartbeat_age_seconds(room_id: str) -> Optional[float]:
    """距最近一次心跳的秒数（无记录返回 None）。"""
    item = _HEARTBEATS.get(room_id)
    if item is None:
        return None
    return (datetime.now(timezone.utc) - item["lastSeenAt"]).total_seconds()


def latest_heartbeat() -> Optional[dict]:
    """全局最近一次心跳（给 `/api/stt/status` 用；含 roomId）。"""
    if not _HEARTBEATS:
        return None
    room_id, item = max(_HEARTBEATS.items(), key=lambda kv: kv[1]["lastSeenAt"])
    return {"roomId": room_id, **item}

