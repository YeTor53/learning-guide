"""r012 用例：在线心跳（`POST /api/presence`）与在线判据。

口径来源：docs/rounds/r012-superadmin-console/design.md §2.6（Q14=2 前端短轮询）。
零网络：只打自己的后端接口，不碰 LiveKit / LLM / STT。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from helpers import register_user, session_cookie

from app.repositories import users as users_repo
from app.services import presence as presence_service


def login(client, user) -> None:
    name, value = session_cookie(user.id)
    client.cookies.set(name, value)


def test_presence_requires_login(client, db) -> None:
    resp = client.post("/api/presence")
    assert resp.status_code == 401, resp.text
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_presence_writes_last_seen_and_counts_as_online(client, db) -> None:
    user = register_user(db, "心跳同学")
    login(client, user)
    assert users_repo.get_user_by_id(db, user.id).last_seen_at is None   # 未上报前没有心跳

    resp = client.post("/api/presence")
    assert resp.status_code == 200, resp.text
    payload = resp.json()["data"]
    assert payload["ok"] is True
    assert payload["lastSeenAt"]

    row = users_repo.get_user_by_id(db, user.id)
    assert row.last_seen_at is not None
    assert presence_service.is_online(row.last_seen_at) is True
    assert user.id in presence_service.online_user_ids(db)


def test_stale_heartbeat_is_offline(db) -> None:
    """判据窗口：超过 `PRESENCE_ONLINE_SECONDS` 的心跳一律离线（不改配置，直接造数据）。"""
    user = register_user(db, "掉线同学")
    stale = datetime.now(timezone.utc) - timedelta(seconds=600)
    users_repo.touch_last_seen(db, user.id, stale)

    row = users_repo.get_user_by_id(db, user.id)
    assert row.last_seen_at is not None
    assert presence_service.is_online(row.last_seen_at) is False
    assert user.id not in presence_service.online_user_ids(db)


def test_is_online_pure_function() -> None:
    """纯函数：无心跳记录 = 离线；窗口可显式指定（不读配置）。"""
    now = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)
    assert presence_service.is_online(None, now=now) is False
    assert presence_service.is_online(now - timedelta(seconds=119), now=now, window_seconds=120) is True
    assert presence_service.is_online(now - timedelta(seconds=121), now=now, window_seconds=120) is False
