"""讨论纪要（r008，作业必做「会后产出」）。

设计事实源：`docs/rounds/r008-assignment-gaps/design.md` §2.5；决定见 ADR-0018。
纪律（同 `services/livekit.py`）：
- 只读 `Settings`，不 import repositories 之外的层，不做 HTTP；
- 外部调用（LLM）集中在 `call_llm`，**失败不回滚业务事实**（ADR-0011 条 4）：失败也落 `failed` 行并记原因；
- `client` 参数可注入（用例打桩），生产走 `call_llm`。
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Callable, Optional

import aiohttp
from psycopg import Connection

from app.api.errors import (
    ERR_FORBIDDEN,
    ERR_LLM_NOT_CONFIGURED,
    ERR_NOT_FOUND,
    ERR_SUMMARY_FAILED,
    AppError,
)
from app.config import Settings, load_settings
from app.repositories import summaries as summaries_repo
from app.repositories.summaries import NewSummary, SummaryRow
from app.schemas.auth import UserVO
from app.schemas.summary import SessionSummaryVO
from app.security.ids import new_id
from app.services import rooms as rooms_service

logger = logging.getLogger(__name__)

MESSAGE_LIMIT = 200
LLM_TIMEOUT_SECONDS = 60

SYSTEM_PROMPT = (
    "你是学习讨论室的记录员。根据给定的房间信息、成员与聊天/发言记录，写一份**中文**讨论纪要，"
    "用 Markdown，分节：## 主题与背景 / ## 讨论要点（3~6 条，可带发言人）/ ## 分歧与未决（如有）/ "
    "## 待办与下一步 / ## 一句话总结。"
    "要求：只依据给定材料，**不要编造**没有出现过的观点或人名；材料不足时明确说明；总长 300~600 字。"
)


class LlmNotConfigured(Exception):
    """未配置 LLM 密钥（映射 503 `LLM_NOT_CONFIGURED`）。"""


class LlmError(Exception):
    """LLM 调用失败或返回空内容（映射 502 `SUMMARY_FAILED`）。"""


LlmClient = Callable[[list[dict]], str]


@dataclass(frozen=True)
class SummaryInput:
    """纪要素材（也是 `input_digest` 的来源，便于复核「用了多少料」）。"""

    room_id: str
    title: str
    topic_label: str
    description: str
    host_name: str
    member_lines: tuple[str, ...]
    message_lines: tuple[str, ...]
    digest: str

    def as_text(self) -> str:
        return (
            f"房间主题：{self.topic_label}\n"
            f"标题：{self.title}\n"
            f"简介：{self.description or '（无）'}\n"
            f"房主：{self.host_name}\n\n"
            f"成员（{len(self.member_lines)} 人）：\n" + "\n".join(self.member_lines) + "\n\n"
            f"讨论记录（{len(self.message_lines)} 条）：\n" + "\n".join(self.message_lines)
        )


def _settings(settings: Optional[Settings] = None) -> Settings:
    return settings if settings is not None else load_settings()


def call_llm(messages: list[dict], settings: Optional[Settings] = None) -> str:
    """唯一 LLM 出口：OpenAI 兼容 `/chat/completions`（aiohttp，60s 超时）。

    未配置密钥 → `LlmNotConfigured`；网络/非 200/空内容 → `LlmError`。
    """
    s = _settings(settings)
    if not s.llm_api_key or not s.llm_base_url:
        raise LlmNotConfigured("未配置 LLM（LLM_API_KEY / LLM_BASE_URL）")

    url = s.llm_base_url.rstrip("/") + "/chat/completions"

    async def _post() -> str:
        timeout = aiohttp.ClientTimeout(total=LLM_TIMEOUT_SECONDS)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                url,
                headers={"Authorization": f"Bearer {s.llm_api_key}", "Content-Type": "application/json"},
                json={"model": s.llm_model, "messages": messages, "temperature": 0.3},
            ) as resp:
                if resp.status != 200:
                    body = (await resp.text())[:300]
                    raise LlmError(f"LLM HTTP {resp.status}: {body}")
                data = await resp.json()
        choices = data.get("choices") or []
        content = (choices[0].get("message", {}).get("content") or "").strip() if choices else ""
        if not content:
            raise LlmError("LLM 返回空内容")
        return content

    try:
        return asyncio.run(_post())
    except LlmError:
        raise
    except Exception as exc:  # noqa: BLE001 —— 网络/解析异常统一映射
        raise LlmError(f"{type(exc).__name__}: {exc}") from exc


def build_summary_input(conn: Connection, room_id: str) -> SummaryInput:
    """素材 = 房间 + 成员 + 最近消息（复用 `rooms.get_room_detail`，它已是唯一组装点）。"""
    detail = rooms_service.get_room_detail(conn, None, room_id)
    room = detail.room
    member_lines = tuple(
        f"- {m.display_name}（{m.role}，{'在房间里' if m.status == 'active' else '已离开'}）"
        for m in detail.members
    )
    message_lines = tuple(
        f"[{m.created_at.strftime('%H:%M')}] {m.display_name}：{m.body}"
        + ("（系统）" if m.kind == "system" else "")
        for m in detail.messages
    )
    digest = f"messages={len(message_lines)};members={len(member_lines)};topic={room.topic_label}"
    return SummaryInput(
        room_id=room.id,
        title=room.title,
        topic_label=room.topic_label,
        description=room.description,
        host_name=room.host_name,
        member_lines=member_lines,
        message_lines=message_lines,
        digest=digest,
    )


def render_messages(payload: SummaryInput) -> list[dict]:
    """OpenAI 兼容 messages（system 指令 + user 素材）。"""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": payload.as_text()},
    ]


def _vo(row: SummaryRow) -> SessionSummaryVO:
    return SessionSummaryVO(
        id=row.id,
        room_id=row.room_id,
        status=row.status,
        provider=row.provider,
        model=row.model,
        input_digest=row.input_digest,
        content=row.content,
        error=row.error,
        created_by=row.created_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def generate_summary(
    conn: Connection,
    actor: UserVO,
    room_id: str,
    *,
    client: Optional[LlmClient] = None,
) -> SessionSummaryVO:
    """生成/重生纪要（Host/Moderator；房间可为 `ended`）。

    - 未配置密钥：不落库，抛 503 `LLM_NOT_CONFIGURED`；
    - 调用失败/空内容：落 `failed` 行（记 error）后抛 502 `SUMMARY_FAILED`（可重试覆盖）；
    - 成功：落 `ready` 行（覆盖同一行，`updated_at` 前进）并返回。
    """
    settings = load_settings()
    with conn.transaction():
        item = rooms_service.assert_room_exists(conn, room_id)
        rooms_service.assert_manager_role(conn, actor, item.room)
        payload = build_summary_input(conn, room_id)

    provider = settings.llm_base_url
    model = settings.llm_model
    summary_id = new_id("sum")
    runner: LlmClient = client or (lambda messages: call_llm(messages, settings))

    try:
        content = (runner(render_messages(payload)) or "").strip()
        if not content:
            raise LlmError("LLM 返回空内容")
    except LlmNotConfigured as exc:
        raise AppError(ERR_LLM_NOT_CONFIGURED, f"未配置纪要模型：{exc}", status=503) from exc
    except LlmError as exc:
        with conn.transaction():
            summaries_repo.upsert_summary(
                conn,
                NewSummary(
                    id=summary_id, room_id=room_id, status="failed", provider=provider, model=model,
                    input_digest=payload.digest, content="", error=str(exc)[:1000], created_by=actor.id,
                ),
            )
        raise AppError(ERR_SUMMARY_FAILED, f"纪要生成失败：{exc}", status=502) from exc

    with conn.transaction():
        summaries_repo.upsert_summary(
            conn,
            NewSummary(
                id=summary_id, room_id=room_id, status="ready", provider=provider, model=model,
                input_digest=payload.digest, content=content, error=None, created_by=actor.id,
            ),
        )
    row = summaries_repo.get_summary(conn, room_id)
    if row is None:
        raise AppError(ERR_NOT_FOUND, "生成后读不到纪要", status=500)
    return _vo(row)


def get_summary(conn: Connection, actor: UserVO, room_id: str) -> Optional[SessionSummaryVO]:
    """查看纪要：在册/历史成员或 Host/Moderator 可见，其他登录用户 403。"""
    item = rooms_service.assert_room_exists(conn, room_id)
    try:
        rooms_service.assert_manager_role(conn, actor, item.room)
    except AppError:
        members = rooms_service.list_members_for_visibility(conn, room_id)
        if actor.id not in members:
            raise AppError(ERR_FORBIDDEN, "只有这间房的成员可以查看纪要", status=403)
    row = summaries_repo.get_summary(conn, room_id)
    return _vo(row) if row else None
