"""r008 纪要接口用例（LLM 一律打桩，不联网；库侧走真实 PostgreSQL 的回滚事务）。

设计事实源：`docs/rounds/r008-assignment-gaps/design.md` §2.5/§2.8；ADR-0018。
"""
from __future__ import annotations

import dataclasses

import pytest

from app.config import Settings, load_settings
from app.services import summary as summary_service
from helpers import register_user, session_cookie

TOPIC = {"topic": "custom", "topicLabel": "纪要", "title": "纪要房", "description": ""}


def login(client, user) -> None:
    name, value = session_cookie(user.id)
    client.cookies.set(name, value)


def create_room(client, title: str = "纪要房") -> dict:
    resp = client.post("/api/rooms", json={**TOPIC, "title": title})
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def test_generate_requires_manager(client, db) -> None:
    """非 Host/Moderator → 403（在册成员也不行：纪要是管理动作）。"""
    host = register_user(db, "房主")
    other = register_user(db, "路人")
    login(client, host)
    room = create_room(client)

    login(client, other)
    resp = client.post(f"/api/rooms/{room['id']}/summary")
    assert resp.status_code == 403, resp.text


def test_generate_then_regenerate_overwrites_same_row(client, db, monkeypatch) -> None:
    """成功写 ready；重复生成 = 覆盖同一行（room_id 唯一），内容更新。"""
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)

    monkeypatch.setattr(summary_service, "call_llm", lambda messages, settings=None: "第一版纪要")
    first = client.post(f"/api/rooms/{room['id']}/summary")
    assert first.status_code == 201, first.text
    body = first.json()["data"]
    assert body["status"] == "ready" and body["content"] == "第一版纪要"
    assert body["inputDigest"], body

    monkeypatch.setattr(summary_service, "call_llm", lambda messages, settings=None: "第二版纪要")
    second = client.post(f"/api/rooms/{room['id']}/summary")
    assert second.status_code == 201, second.text
    again = second.json()["data"]
    assert again["id"] == body["id"], "覆盖式重生应写同一行"
    assert again["content"] == "第二版纪要"

    cur = db.execute("SELECT count(*) FROM session_summaries WHERE room_id = %s", (room["id"],))
    assert cur.fetchone()[0] == 1


def test_not_configured_returns_503_and_keeps_no_row(client, db, monkeypatch) -> None:
    """未配置密钥 → 503 LLM_NOT_CONFIGURED，且**不落库**（避免留下空纪要）。"""
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)

    base = load_settings()
    bare = dataclasses.replace(base, llm_api_key="")
    monkeypatch.setattr(summary_service, "load_settings", lambda: bare)

    resp = client.post(f"/api/rooms/{room['id']}/summary")
    assert resp.status_code == 503, resp.text
    assert resp.json()["error"]["code"] == "LLM_NOT_CONFIGURED"
    cur = db.execute("SELECT count(*) FROM session_summaries WHERE room_id = %s", (room["id"],))
    assert cur.fetchone()[0] == 0


def test_failed_call_records_failed_row_and_502(client, db, monkeypatch) -> None:
    """外部调用失败 → 502 SUMMARY_FAILED，并落一条 failed 行（留痕、可重试覆盖）。"""
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)

    def boom(messages, settings=None):
        raise summary_service.LlmError("模拟超时")

    monkeypatch.setattr(summary_service, "call_llm", boom)
    resp = client.post(f"/api/rooms/{room['id']}/summary")
    assert resp.status_code == 502, resp.text
    assert resp.json()["error"]["code"] == "SUMMARY_FAILED"

    cur = db.execute("SELECT status, error FROM session_summaries WHERE room_id = %s", (room["id"],))
    row = cur.fetchone()
    assert row is not None and row[0] == "failed" and "模拟超时" in row[1]


def test_get_summary_visibility_and_empty(client, db, monkeypatch) -> None:
    """未生成 → null；成员可见；非成员 403。"""
    host = register_user(db, "房主")
    member = register_user(db, "成员")
    outsider = register_user(db, "外人")
    login(client, host)
    room = create_room(client)

    monkeypatch.setattr(summary_service, "call_llm", lambda messages, settings=None: "纪要正文")
    assert client.post(f"/api/rooms/{room['id']}/summary").status_code == 201

    # 申请人加入（走真实等候室流程）
    login(client, member)
    created = client.post(f"/api/rooms/{room['id']}/join-requests", json={"message": ""})
    request_id = created.json()["data"]["id"]
    login(client, host)
    assert client.post(f"/api/join-requests/{request_id}/approve").status_code == 200

    login(client, member)
    resp = client.get(f"/api/rooms/{room['id']}/summary")
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["summary"]["content"] == "纪要正文"

    login(client, outsider)
    assert client.get(f"/api/rooms/{room['id']}/summary").status_code == 403

    # 未生成的房间：成员看到 null
    login(client, host)
    empty_room = create_room(client, title="没生成过的房间")
    empty = client.get(f"/api/rooms/{empty_room['id']}/summary")
    assert empty.status_code == 200
    assert empty.json()["data"]["summary"] is None


def test_host_can_generate_after_room_ended(client, db, monkeypatch) -> None:
    """房间结束后房主仍能生成纪要（作业流程：结束后看纪要）；详情里 myRoleAny 保留历史身份。"""
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    assert client.post(f"/api/rooms/{room['id']}/end").status_code == 200

    detail = client.get(f"/api/rooms/{room['id']}").json()["data"]["room"]
    assert detail["myRole"] is None, "结束后活跃角色应为空"
    assert detail["myRoleAny"] == "host", detail

    monkeypatch.setattr(summary_service, "call_llm", lambda messages, settings=None: "结束后的纪要")
    resp = client.post(f"/api/rooms/{room['id']}/summary")
    assert resp.status_code == 201, resp.text
    assert resp.json()["data"]["content"] == "结束后的纪要"
