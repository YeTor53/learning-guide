"""进程内 pub/sub（r012）：SSE 只推**通知型事件**，HTTP 落库仍是唯一真相。

设计事实源：docs/rounds/r012-superadmin-console/design.md §4.3、ADR-0025 D3/D4。
- 单进程内存态：进程重启丢订阅（前端靠重连 + 30 秒轮询兜底）；
- `publish` 同步非阻塞：队列满时丢最旧并记日志，**绝不阻塞发布方**；
- 订阅者数超上限 → `subscribe()` 抛 503（不静默丢弃，便于观察）；
- 事件 id 单调递增（供 SSE 的 `id:` 字段，支撑断线续传语义）。
"""
from __future__ import annotations

import asyncio
import itertools
import json
import logging
from typing import Any, Optional

from app.api.errors import AppError
from app.config import load_settings

logger = logging.getLogger("app")

_subscribers: set["Subscriber"] = set()
_event_ids = itertools.count(1)


class Subscriber:
    """一个 SSE 连接的收件箱（每条连接一个）。"""

    def __init__(self, maxsize: int) -> None:
        self.queue: "asyncio.Queue[dict]" = asyncio.Queue(maxsize=maxsize)
        self.closed = False

    def close(self) -> None:
        self.closed = True


def subscriber_count() -> int:
    return len(_subscribers)


def next_event_id() -> int:
    return next(_event_ids)


def subscribe() -> Subscriber:
    """登记一个订阅者；超过上限抛 503（`SSE_MAX_SUBSCRIBERS`）。"""
    settings = load_settings()
    if len(_subscribers) >= settings.sse_max_subscribers:
        raise AppError("INTERNAL", "实时通道连接数已达上限，请稍后重试", status=503)
    subscriber = Subscriber(maxsize=settings.sse_subscriber_queue_max)
    _subscribers.add(subscriber)
    return subscriber


def unsubscribe(subscriber: Subscriber) -> None:
    subscriber.close()
    _subscribers.discard(subscriber)


def publish(event_type: str, payload: dict[str, Any]) -> None:
    """向所有订阅者投递一条通知（同步、非阻塞）。"""
    if not _subscribers:
        return
    event = {"id": next_event_id(), "type": event_type, "payload": payload}
    for subscriber in list(_subscribers):
        if subscriber.closed:
            continue
        try:
            subscriber.queue.put_nowait(event)
        except asyncio.QueueFull:
            # 该端消费太慢：丢最旧的一条再塞新的（保新不保旧），并记账
            try:
                subscriber.queue.get_nowait()
                subscriber.queue.put_nowait(event)
            except (asyncio.QueueEmpty, asyncio.QueueFull):  # pragma: no cover - 竞态兜底
                pass
            logger.warning("SSE 订阅者队列已满，丢弃最旧事件（type=%s）", event_type)


def reset() -> None:
    """测试用：清空订阅者与事件计数。"""
    global _event_ids
    for subscriber in list(_subscribers):
        unsubscribe(subscriber)
    _event_ids = itertools.count(1)


def encode_sse(event: Optional[dict] = None) -> str:
    """SSE 帧编码（唯一出口，前后端共用一份口径，见 design §4.4）。"""
    if event is None:
        return ": ping\n\n"
    body = _json({"type": event["type"], "payload": event["payload"]})
    return f"id: {event['id']}\nevent: notify\ndata: {body}\n\n"


def _json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
