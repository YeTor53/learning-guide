"""r013：worker 侧「有限重试」纯函数（不依赖 livekit，便于后端 env 单测）。

背景：`backend/agents/transcriber.py` 的 `ctx.connect()` 实测会因 LiveKit FFI 一次性 panic 退出
（`timed out waiting for ReadyForRoomEventRequest`），此前是**裸崩**——`agents.bat` 靠外层循环重启，
但崩溃原因不可观测、也没上报给后端。这里把「重试 + 退避 + 记录最后一次错误」抽成纯函数，
worker 与用例共用同一份实现。

纪律：本模块**只用标准库**（worker 跑在独立环境 `lg_agents`，不假设后端依赖在场）。
"""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, Optional, Sequence, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def retry_async(
    action: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    backoff: Sequence[float] = (2.0, 4.0),
    label: str = "操作",
    on_error: Optional[Callable[[int, BaseException], None]] = None,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> T:
    """执行 `action`，失败按 `backoff` 退避重试，最多 `attempts` 次。

    - 成功：返回结果；
    - 全部失败：**抛最后一次异常**（由调用方决定是否退出进程），并在日志里留下每次的尝试序号与异常摘要；
    - `on_error(attempt, exc)`：可选回调（调用方用它记「最后一次错误」供心跳上报）。
    """
    if attempts < 1:
        raise ValueError("attempts 必须 ≥ 1")
    last: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await action()
        except BaseException as exc:  # noqa: BLE001 —— 故意兜住（含 CancelledError 之外的一切）
            if isinstance(exc, asyncio.CancelledError):
                raise
            last = exc
            logger.warning("%s 第 %d/%d 次失败：%s: %s", label, attempt, attempts, type(exc).__name__, exc)
            if on_error is not None:
                on_error(attempt, exc)
            if attempt < attempts:
                delay = backoff[min(attempt - 1, len(backoff) - 1)] if backoff else 0.0
                if delay:
                    await sleep(delay)
    assert last is not None
    raise last
