"""r012 用例：全服大屏聊天（发 / 列 / 限流 / 在线点）与 SSE 通知通道。

口径来源：docs/rounds/r012-superadmin-console/design.md §4、ADR-0025；需求单 §10.1（Q13=1）。
约定：零网络、零配额（不打 LiveKit/LLM）；SSE 用 httpx 流式读前几帧即关闭。
"""
from __future__ import annotations

import asyncio
import json

import pytest

from app.services import events as events_service
from app.services import global_chat as global_chat_service
from helpers import register_user, session_cookie


def login(client, user) -> None:
    name, value = session_cookie(user.id)
    client.cookies.set(name, value)


def post_message(client, body: str) -> dict:
    resp = client.post("/api/global-messages", json={"body": body})
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


# ---------------- 读 ----------------

def test_visitor_can_read_but_not_post(client, db) -> None:
    guest = register_user(db, "发过言的")
    login(client, guest)
    post_message(client, "大家好")

    client.cookies.clear()
    listed = client.get("/api/global-messages")
    assert listed.status_code == 200, listed.text
    assert [item["body"] for item in listed.json()["data"]["items"]] == ["大家好"]

    denied = client.post("/api/global-messages", json={"body": "路人来一句"})
    assert denied.status_code == 401
    assert denied.json()["error"]["code"] == "UNAUTHORIZED"


def test_messages_are_ordered_and_cursor_pages_back(client, db) -> None:
    user = register_user(db, "话多的")
    login(client, user)
    for index in range(3):
        post_message(client, f"第 {index} 条")

    items = client.get("/api/global-messages").json()["data"]["items"]
    assert [item["body"] for item in items] == ["第 0 条", "第 1 条", "第 2 条"]   # 正序返回

    older = client.get(f"/api/global-messages?before_id={items[-1]['id']}").json()["data"]["items"]
    assert [item["body"] for item in older] == ["第 0 条", "第 1 条"]


def test_author_online_flag_follows_heartbeat(client, db) -> None:
    from datetime import datetime, timedelta, timezone

    from app.repositories import users as users_repo

    speaker = register_user(db, "说话的")
    login(client, speaker)
    assert client.post("/api/presence").status_code == 200   # 在线 = 最近有心跳（Q14=2）
    post_message(client, "我在线")

    items = client.get("/api/global-messages").json()["data"]["items"]
    assert items[0]["authorOnline"] is True

    users_repo.touch_last_seen(db, speaker.id, datetime.now(timezone.utc) - timedelta(hours=1))
    stale = client.get("/api/global-messages").json()["data"]["items"]
    assert stale[0]["authorOnline"] is False


# ---------------- 写 ----------------

def test_body_length_and_blank_validation(client, db) -> None:
    user = register_user(db, "边界")
    login(client, user)
    assert client.post("/api/global-messages", json={"body": ""}).status_code == 400
    assert client.post("/api/global-messages", json={"body": "   "}).status_code == 400
    assert client.post("/api/global-messages", json={"body": "x" * 501}).status_code == 400
    assert client.post("/api/global-messages", json={"body": "x" * 500}).status_code == 201


def test_rate_limit_returns_429(client, db) -> None:
    from app.config import load_settings

    settings = load_settings()
    user = register_user(db, "刷屏的")
    login(client, user)
    for _ in range(settings.global_chat_rate_limit):
        post_message(client, "同一条")
    limited = client.post("/api/global-messages", json={"body": "再来一条"})
    assert limited.status_code == 429, limited.text
    assert limited.json()["error"]["code"] == "RATE_LIMITED"

    # 限流不落库：窗口内条数 == 上限
    assert global_chat_service.list_messages(db, None, limit=100)[-1].body == "同一条"
    assert len(global_chat_service.list_messages(db, None, limit=100)) == settings.global_chat_rate_limit


def test_posting_publishes_notification_event(client, db) -> None:
    events_service.reset()
    subscriber = events_service.subscribe()
    try:
        user = register_user(db, "发言者")
        login(client, user)
        message = post_message(client, "广播这一条")
        event = asyncio.run(asyncio.wait_for(subscriber.queue.get(), timeout=1))
    finally:
        events_service.reset()

    assert event["type"] == "global_message"
    assert event["payload"] == {"id": message["id"]}


# ---------------- SSE 通道 ----------------

def test_events_route_is_registered(client) -> None:
    """路由确实挂在 /api/events（不回 404），且用 text/event-stream 承载。"""
    from app.main import create_app

    paths = set(create_app().openapi()["paths"])
    assert "/api/events" in paths
    assert "/api/global-messages" in paths


def test_events_stream_emits_retry_then_notify(client, db) -> None:
    """直接驱动响应生成器（SSE 是**永不结束**的流，不走 TestClient 的流式收尾）。

    判据：首帧 `retry: 3000`、订阅后 publish 得到 `id: … / event: notify / data: {最小载荷}`；
    保活帧走同一个编码函数（真实间隔 = `SSE_KEEPALIVE_SECONDS`）。
    """
    from app.api.routers import events as events_router

    class _Request:
        async def is_disconnected(self) -> bool:
            return False

    events_service.reset()

    async def scenario() -> tuple[object, str, str]:
        response = await events_router.stream_events(_Request(), user=None)
        assert response.media_type == "text/event-stream"
        assert response.headers["x-accel-buffering"] == "no"
        assert response.headers["cache-control"] == "no-cache, no-store"

        generator = response.body_iterator
        first = await anext(generator)                       # retry 帧
        events_service.publish("global_message", {"id": "gmsg_test"})
        frame = await asyncio.wait_for(anext(generator), timeout=2)
        await generator.aclose()
        return response, str(first), str(frame)

    response, first, frame = asyncio.run(scenario())
    events_service.reset()

    assert first == "retry: 3000\n\n"
    assert frame.startswith("id: 1\nevent: notify\ndata: ")
    assert json.loads(frame.split("data: ", 1)[1].strip()) == {
        "type": "global_message",
        "payload": {"id": "gmsg_test"},
    }
    # 事件名固定 notify（避免前端漏解多事件名）；`data` 里同时带 type 与最小载荷
    assert response.headers["connection"] == "keep-alive"
    assert events_service.encode_sse(None) == ": ping\n\n"   # 保活帧（未产出事件时每 SSE_KEEPALIVE_SECONDS 一行）


def test_subscriber_cap_returns_503(client, db, monkeypatch) -> None:
    from app.config import reset_settings_cache

    events_service.reset()
    monkeypatch.setenv("SSE_MAX_SUBSCRIBERS", "1")
    reset_settings_cache()
    first = events_service.subscribe()
    try:
        with pytest.raises(Exception) as exc:
            events_service.subscribe()
        assert getattr(exc.value, "status", None) == 503
    finally:
        events_service.unsubscribe(first)
        events_service.reset()
        monkeypatch.delenv("SSE_MAX_SUBSCRIBERS", raising=False)
        reset_settings_cache()
