"""并发用例：两个线程同时批准最后一个名额。

设计事实源：docs/02-modules/r001-rooms.md §8（并发）、§9（验证矩阵最后一行）
判据：恰好 1 个成功、1 个 `ROOM_FULL`，且库里活跃成员数 = `capacity`。
说明：这条用例必须用**两条真实连接 + 已提交数据**才能验证行锁，所以不走"必定回滚"夹具，
      改为自建数据、跑完在 finally 里删除（删房间会级联清成员与申请）。
"""
from __future__ import annotations

import threading

import pytest

from app.api.errors import AppError
from app.db.pool import get_conn
from app.repositories import rooms as repo
from app.schemas.auth import RegisterIn
from app.services import auth as auth_service
from app.services import rooms as rooms_service


@pytest.fixture()
def committed_room(pool):
    """建一个 capacity=3、已有 2 名成员（房主 + 1 人）、2 条待批申请的房间——只剩 1 个名额。"""
    setup = get_conn()
    conn = setup.__enter__()
    try:
        host = auth_service.register(conn, RegisterIn(email="cc-host@example.com", display_name="并发房主", password="demo-pass-123"))
        members = [
            auth_service.register(conn, RegisterIn(email=f"cc-m{i}@example.com", display_name=f"并发成员{i}", password="demo-pass-123"))
            for i in range(3)  # 0 号已是成员；1、2 号各有一条待批申请
        ]
        room_id = "room_cc_test"
        conn.execute(
            """INSERT INTO rooms (id, host_id, topic, topic_label, title, capacity, room_code)
               VALUES (%s, %s, 'custom', '并发', '并发测试房间', 3, 'CC0001')
               ON CONFLICT (id) DO NOTHING""",
            (room_id, host.id),
        )
        conn.execute(
            """INSERT INTO room_members (id, room_id, user_id, role) VALUES ('mem_cc_host', %s, %s, 'host')
               ON CONFLICT (id) DO NOTHING""",
            (room_id, host.id),
        )
        conn.execute(
            """INSERT INTO room_members (id, room_id, user_id, role) VALUES ('mem_cc_0', %s, %s, 'participant')
               ON CONFLICT (id) DO NOTHING""",
            (room_id, members[0].id),
        )
        conn.execute(
            """INSERT INTO join_requests (id, room_id, user_id, message) VALUES ('req_cc_1', %s, %s, '并发申请一')
               ON CONFLICT (id) DO NOTHING""",
            (room_id, members[1].id),
        )
        conn.execute(
            """INSERT INTO join_requests (id, room_id, user_id, message) VALUES ('req_cc_2', %s, %s, '并发申请二')
               ON CONFLICT (id) DO NOTHING""",
            (room_id, members[2].id),
        )
        conn.commit()
    finally:
        setup.__exit__(None, None, None)

    yield {"room_id": room_id, "host": host, "user_ids": [host.id, *(m.id for m in members)]}

    cleanup = get_conn()
    conn = cleanup.__enter__()
    try:
        conn.execute("DELETE FROM rooms WHERE id = %s", (room_id,))
        conn.execute("DELETE FROM users WHERE id = ANY(%s)", (list({host.id, *(m.id for m in members)}),))
        conn.commit()
    finally:
        cleanup.__exit__(None, None, None)


def test_concurrent_approve_last_slot(committed_room) -> None:
    room_id = committed_room["room_id"]
    host_id = committed_room["host"].id
    outcomes: list[str] = []
    lock = threading.Lock()
    barrier = threading.Barrier(2)

    def approve(request_id: str) -> None:
        with get_conn() as conn:
            barrier.wait(timeout=10)  # 尽量让两个线程同时进入 service
            try:
                rooms_service.approve_join_request(conn, _host_vo(host_id), request_id)
                result = "ok"
            except AppError as exc:
                result = exc.code
            with lock:
                outcomes.append(result)

    threads = [threading.Thread(target=approve, args=(rid,)) for rid in ("req_cc_1", "req_cc_2")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=20)

    assert sorted(outcomes) == ["ROOM_FULL", "ok"], outcomes
    with get_conn() as conn:
        active = repo.count_active_members(conn, room_id)
    assert active == 3  # == capacity


def _host_vo(user_id: str):
    """构造一个只带 id 的 actor（service 只用 actor.id 与角色判定）。"""
    from datetime import datetime, timezone

    from app.schemas.auth import UserVO

    return UserVO(id=user_id, email="cc-host@example.com", display_name="并发房主", created_at=datetime.now(timezone.utc))
