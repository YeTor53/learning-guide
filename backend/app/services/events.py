"""进程内 pub/sub（r012）：SSE 只推**通知型事件**，HTTP 落库仍是唯一真相。

设计事实源：docs/rounds/r012-superadmin-console/design.md §4.3、ADR-0025 D3/D4。
- 单进程内存态：进程重启丢订阅（前端靠重连 + 30 秒轮询兜底）；
- `publish` 同步非阻塞且**线程安全**：发布方可能是跑在线程池里的同步端点（FastAPI 的 `def` 路由），
  所以一律经订阅者自己的事件循环 `call_soon_threadsafe` 投递——直接 `put_nowait` 会从别的线程唤醒
  `queue.get()` 的等待者（非线程安全），实测会把整个事件循环卡死（2026-09-20 真机踩到）；
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

    def __init__(self, maxsize: int, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        self.queue: "asyncio.Queue[dict]" = asyncio.Queue(maxsize=maxsize)
        # 订阅发生在事件循环内（SSE 处理器）——记下它，供**其它线程**安全投递。
        # 极少数同步环境（纯同步用例直接调 subscribe）拿不到循环 → 记 None，投递时退化为同线程直投。
        if loop is not None:
            self.loop: Optional[asyncio.AbstractEventLoop] = loop
        else:
            try:
                self.loop = asyncio.get_running_loop()
            except RuntimeError:
                self.loop = None
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
    subscriber = Subscriber(maxsize=settings.sse_subscriber_queue_max)  # loop = 当前运行中的循环
    _subscribers.add(subscriber)
    return subscriber


def unsubscribe(subscriber: Subscriber) -> None:
    subscriber.close()
    _subscribers.discard(subscriber)


def _offer(subscriber: Subscriber, event: dict) -> None:
    """真正的投递（**只在订阅者的循环线程里跑**）：队列满时丢最旧，保新不保旧。"""
    if subscriber.closed:
        return
    try:
        subscriber.queue.put_nowait(event)
    except asyncio.QueueFull:
        try:
            subscriber.queue.get_nowait()
            subscriber.queue.put_nowait(event)
        except (asyncio.QueueEmpty, asyncio.QueueFull):  # pragma: no cover - 竞态兜底
            pass
        logger.warning("SSE 订阅者队列已满，丢弃最旧事件（type=%s）", event["type"])


def publish(event_type: str, payload: dict[str, Any]) -> None:
    """向所有订阅者投递一条通知（同步、非阻塞、**可从任意线程调用**）。

    同步端点（FastAPI 的 `def` 路由）跑在线程池里，所以这里必须走
    `loop.call_soon_threadsafe`，不能直接 `put_nowait`。
    """
    if not _subscribers:
        return
    event = {"id": next_event_id(), "type": event_type, "payload": payload}
    for subscriber in list(_subscribers):
        if subscriber.closed:
            continue
        loop = subscriber.loop
        if loop is None:   # 无循环信息（仅同步用例）：同线程直投
            _offer(subscriber, event)
            continue
        try:
            loop.call_soon_threadsafe(_offer, subscriber, event)
        except RuntimeError:  # 循环已关闭（连接正在收尾）
            unsubscribe(subscriber)


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
