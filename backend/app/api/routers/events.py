"""SSE 通知通道（r012）：`GET /api/events`。

设计事实源：docs/rounds/r012-superadmin-console/design.md §4.4、ADR-0025 D2/D3。
协议（一次写死，前后端共用）：
- 响应头 `text/event-stream`；事件名固定 `notify`；`data` 是 `{"type": ..., "payload": {...}}` 的最小载荷；
- `retry: 3000` 首帧给出重连间隔；每 `SSE_KEEPALIVE_SECONDS` 秒一行 `: ping` 保活；
- **只推通知**：收到后前端照旧走 HTTP 拉真相（ADR-0013 的沿用）。

**不要给这条路由加任何 DB 依赖**（2026-09-20 真机踩到，ADR-0025 D7）：流是**永不结束**的，
FastAPI 的依赖清理发生在响应结束之后 —— 只要依赖里有一条 `db_conn`，每个订阅者就会把连接池
（`max_size=8`）里的一条连接攥到天荒地老；实测 9 条流就把整站打成 30 秒后 500（`PoolTimeout`）。
本流载荷只有 `{type, payload:{id}}`，是公开通知面，未登录也允许订阅，因此不需要用户身份。
"""
from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.config import load_settings
from app.services import events as events_service

router = APIRouter(tags=["events"])


@router.get("/events", status_code=200)
async def stream_events(request: Request) -> StreamingResponse:
    """订阅通知流（未登录也可订阅：大屏是公开面；**刻意不取数据库连接**，见模块头部注释）。"""
    settings = load_settings()
    subscriber = events_service.subscribe()

    async def generator() -> AsyncIterator[str]:
        try:
            yield "retry: 3000\n\n"          # 前端断线重连间隔（EventSource 自带重连）
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(
                        subscriber.queue.get(), timeout=settings.sse_keepalive_seconds
                    )
                except asyncio.TimeoutError:
                    yield events_service.encode_sse(None)   # `: ping`
                    continue
                yield events_service.encode_sse(event)
        finally:
            events_service.unsubscribe(subscriber)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",     # 反代不缓冲（本机 uvicorn 直连无影响，公网部署时有用）
        },
    )


# 事件载荷形状（供文档与测试引用；实现在 services/events.py::publish）
EVENT_PAYLOAD_EXAMPLE = json.dumps({"type": "global_message", "payload": {"id": "gmsg_xxx"}}, ensure_ascii=False)
