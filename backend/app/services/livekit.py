"""LiveKit 接入：本仓**唯一**接触 LiveKit 与 `LIVEKIT_*` 的模块。

设计事实源：`docs/02-modules/r002-livekit.md` §6.4；约定见 ADR-0011（条 3 Token 无状态 / 条 4 外部调用在事务提交后 / 条 8 唯一出口）。
纪律：
- 只读 `Settings`，不读 `process.env`，不 import repositories，不做权限判断（权限一律在 `services/rooms.py`）；
- 网络调用一律在**事件循环内**构造 `LiveKitAPI`（其 `aiohttp.ClientSession` 需要运行中的 loop），带超时，失败只记日志并返回中性值；
- `issue_token` 是**纯本地签名**，不联网。
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import timedelta
from typing import Any, Callable, Optional

from livekit import api
from livekit.protocol import room as proto_room

from app.config import Settings, load_settings

logger = logging.getLogger(__name__)


def _settings(settings: Optional[Settings]) -> Settings:
    return settings if settings is not None else load_settings()


def issue_token(
    room_name: str,
    user_id: str,
    display_name: str,
    role: str,
    settings: Optional[Settings] = None,
    ttl_seconds: Optional[int] = None,
    max_participants: Optional[int] = None,
    *,
    hidden: bool = False,
    attributes: Optional[dict[str, str]] = None,
    can_publish: bool = True,
    can_publish_data: bool = True,
) -> str:
    """签一张进房 Token（JWT，本地签名，不联网）。

    - `identity` = `user_id`、`name` = 显示名（ADR-0011 条 2）；
    - `room_admin` 仅 Host 为真；
    - TTL 默认按模式派生（cloud 3600 / self 300，ADR-0011 条 3）；
    - `RoomConfiguration.max_participants` 取 `settings.room_capacity`（ADR-0011 条 9 的兜底闸）。

    r012 新增（ADR-0024；**普通成员一律走默认值，行为不变**）：
    - `hidden=True` → `VideoGrants.hidden`：对**其他参与者不可见**（超管隐身，实测字段存在于 livekit-api 1.2.1）；
    - `attributes` → `AccessToken.with_attributes`：随参与者广播的键值（本项目用 `lg-role` 给转写 worker 做过滤）；
    - `can_publish` / `can_publish_data`：超管关掉发布（不发音频/视频/数据通道）——音视频走 LiveKit 计费，超管只管理。
    """
    s = _settings(settings)
    ttl = ttl_seconds if ttl_seconds is not None else s.livekit_token_ttl_seconds
    capacity = max_participants if max_participants is not None else s.room_capacity
    grants = api.VideoGrants(
        room_join=True,
        room=room_name,
        can_publish=can_publish,
        can_subscribe=True,
        can_publish_data=can_publish_data,
        room_admin=(role == "host"),
        hidden=True if hidden else None,   # None = 不写该 claim（保持旧 Token 形状）
    )
    token = (
        api.AccessToken(s.livekit_api_key, s.livekit_api_secret)
        .with_identity(user_id)
        .with_name(display_name)
        .with_grants(grants)
        .with_room_config(api.RoomConfiguration(max_participants=capacity))
        .with_ttl(timedelta(seconds=ttl))
    )
    if attributes:
        token = token.with_attributes(attributes)
    return token.to_jwt()


def _run(call: Callable[[api.LiveKitAPI], Any], settings: Optional[Settings] = None) -> Any:
    """在事件循环内构造 `LiveKitAPI` → 调用 → 关闭；超时或异常记日志并返回 `None`。

    注意：`LiveKitAPI.__init__` 会建 `aiohttp.ClientSession`，必须在运行中的循环里构造
    （在循环外构造会 `RuntimeError: no running event loop`）——实现期实测，见 changes.md。
    """
    s = _settings(settings)

    async def _wrap() -> Any:
        lk = api.LiveKitAPI(s.livekit_url, s.livekit_api_key, s.livekit_api_secret)
        try:
            return await asyncio.wait_for(call(lk), s.livekit_timeout_seconds)
        finally:
            await lk.aclose()

    try:
        return asyncio.run(_wrap())
    except Exception as exc:  # noqa: BLE001 —— 外部服务失败不回滚业务（ADR-0011 条 4）
        logger.warning("LiveKit 调用失败：%s: %s", type(exc).__name__, exc)
        return None


def remove_participant(room_name: str, user_id: str, settings: Optional[Settings] = None) -> bool:
    """移除参与者并（cloud 模式）作废其已签发 Token；返回是否成功。"""
    s = _settings(settings)

    async def call(lk: api.LiveKitAPI) -> Any:
        identity = proto_room.RoomParticipantIdentity(room=room_name, identity=user_id)
        if s.livekit_mode == "cloud":
            # 必须显式传：撤销按 token 的 nbf 判定，默认截止带 1 分钟缓冲（官方文档原文）
            identity.revoke_token_ts = int(time.time())
        return await lk.room.remove_participant(identity)

    return _run(call, s) is not None


def delete_room(room_name: str, settings: Optional[Settings] = None) -> bool:
    """删除 LiveKit 房间（强制断开全部连接）；返回是否成功。"""

    async def call(lk: api.LiveKitAPI) -> Any:
        return await lk.room.delete_room(proto_room.DeleteRoomRequest(room=room_name))

    return _run(call, settings) is not None


def ensure_transcriber(room_id: str, settings: Optional[Settings] = None) -> str:
    """确保转写 worker 会被派进该房间；返回 `"created"` / `"dispatched"` / `""`（失败）。

    口径（ADR-0023）：`STT_MODE=agent` 时，建房即把 agent 一起建进去（`CreateRoomRequest.agents`）；
    房间已存在（比如建房后 LiveKit 侧已建）则退回**显式派单**。失败只记日志、不影响建房与取票
    （与 `_run` 的中性值纪律一致：外部调用失败不改业务真相）。
    """
    s = _settings(settings)
    if s.stt_mode != "agent":
        return ""

    async def call(lk: api.LiveKitAPI) -> str:
        try:
            await lk.room.create_room(
                proto_room.CreateRoomRequest(
                    name=room_id,
                    empty_timeout=600,
                    agents=[proto_room.RoomAgentDispatch(agent_name=s.stt_agent_name)],
                )
            )
            return "created"
        except Exception:  # noqa: BLE001 —— 房间已存在等：退回显式派单
            await lk.agent_dispatch.create_dispatch(
                api.CreateAgentDispatchRequest(room=room_id, agent_name=s.stt_agent_name)
            )
            return "dispatched"

    out = _run(call, s)
    if not out:
        logger.warning("转写 worker 派单失败（不影响建房）：room=%s agent=%s", room_id, s.stt_agent_name)
    return out or ""


def list_participant_identities(room_name: str, settings: Optional[Settings] = None) -> list[str]:
    """房间内在场的 identity 列表（取证与排障用；前端在场由 SDK 事件驱动，不走这里）。"""

    async def call(lk: api.LiveKitAPI) -> Any:
        res = await lk.room.list_participants(proto_room.ListParticipantsRequest(room=room_name))
        return [p.identity for p in res.participants]

    out = _run(call, settings)
    return list(out) if out else []
