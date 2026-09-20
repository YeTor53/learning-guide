"""r013 用例：worker 连接重试助手（`backend/agents/retry.py`，纯函数、不依赖 livekit）。

背景：worker 的 `ctx.connect()` 实测会因 LiveKit FFI 一次性 panic 失败；`entrypoint` 以前是裸崩，
现在改为「有限重试 → 失败就上报原因并以退出码 2 退出，交给守护重启」。本文件钉住重试语义。
"""
from __future__ import annotations

import asyncio

import pytest

from agents.retry import retry_async


def test_succeeds_after_transient_failures() -> None:
    calls = {"n": 0}
    delays: list[float] = []

    async def action() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("timed out waiting for ReadyForRoomEventRequest")
        return "connected"

    async def fake_sleep(seconds: float) -> None:
        delays.append(seconds)

    result = asyncio.run(retry_async(action, attempts=3, backoff=(2.0, 4.0), sleep=fake_sleep))
    assert result == "connected"
    assert calls["n"] == 3
    assert delays == [2.0, 4.0]          # 第 1、2 次失败后各退避一次；最后一次不再等待


def test_raises_last_error_after_all_attempts() -> None:
    errors: list[tuple[int, str]] = []
    calls = {"n": 0}

    async def action() -> None:
        calls["n"] += 1
        raise RuntimeError(f"boom-{calls['n']}")

    async def fake_sleep(_seconds: float) -> None:
        return None

    with pytest.raises(RuntimeError) as excinfo:
        asyncio.run(retry_async(action, attempts=3, backoff=(0.0,), sleep=fake_sleep,
                                on_error=lambda attempt, exc: errors.append((attempt, str(exc)))))
    assert str(excinfo.value) == "boom-3"          # 抛最后一次，不是第一次
    assert calls["n"] == 3
    assert errors == [(1, "boom-1"), (2, "boom-2"), (3, "boom-3")]


def test_backoff_reuses_last_value_when_shorter() -> None:
    delays: list[float] = []

    async def action() -> None:
        raise RuntimeError("x")

    async def fake_sleep(seconds: float) -> None:
        delays.append(seconds)

    with pytest.raises(RuntimeError):
        asyncio.run(retry_async(action, attempts=4, backoff=(1.0, 3.0), sleep=fake_sleep))
    assert delays == [1.0, 3.0, 3.0]


def test_cancelled_error_is_not_retried() -> None:
    calls = {"n": 0}

    async def action() -> None:
        calls["n"] += 1
        raise asyncio.CancelledError()

    async def fake_sleep(_seconds: float) -> None:
        return None

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(retry_async(action, attempts=3, backoff=(0.0,), sleep=fake_sleep))
    assert calls["n"] == 1


def test_rejects_invalid_attempts() -> None:
    async def action() -> None:
        return None

    with pytest.raises(ValueError):
        asyncio.run(retry_async(action, attempts=0))
