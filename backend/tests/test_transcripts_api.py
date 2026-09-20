"""r010 转写接口用例（STT 一律打桩，不联网；库侧走真实 PostgreSQL 的回滚事务）。

设计事实源：`docs/rounds/r010-transcription/design.md` §2.3~§2.5；ADR-0022；
需求 `docs/00-requirements/r010-transcription.md` 的 E2/E3（E4 三源合一在 cp-2 的用例里覆盖）。
"""
from __future__ import annotations

import dataclasses

import pytest

from app.config import Settings, load_settings
from app.services import stt as stt_service
from app.services import transcripts as transcripts_service
from helpers import register_user, session_cookie

TOPIC = {"topic": "custom", "topicLabel": "转写", "title": "转写房", "description": ""}
AUDIO = b"\x1aE\xdf\xa3fake-webm-audio-bytes"


def login(client, user) -> None:
    name, value = session_cookie(user.id)
    client.cookies.set(name, value)


def create_room(client, title: str = "转写房") -> dict:
    resp = client.post("/api/rooms", json={**TOPIC, "title": title})
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def add_member(db, room_id: str, user_id: str, role: str = "participant") -> None:
    db.execute(
        "INSERT INTO room_members (id, room_id, user_id, role) VALUES (%s, %s, %s, %s)",
        (f"mem_{user_id[-6:]}", room_id, user_id, role),
    )


def stub_stt(monkeypatch, text: str = "今天先聊这一段") -> list[dict]:
    """把「已配置 STT」+「唯一 STT 出口」都换成离线桩（记录调用次数，便于断言重传不重复调）。"""
    configured = dataclasses.replace(
        load_settings(), stt_base_url="https://stt.example.com/v1", stt_api_key="test-key"
    )
    monkeypatch.setattr(transcripts_service, "load_settings", lambda: configured)
    calls: list[dict] = []

    def fake(audio, *, filename, language=None, client=None, settings=None):
        calls.append({"bytes": len(audio), "filename": filename, "language": language})
        return stt_service.SttResult(
            text=text,
            language=language or "zh",
            provider=(settings.stt_base_url if settings else ""),
            model=(settings.stt_model if settings else ""),
        )

    monkeypatch.setattr(stt_service, "call_stt", fake)
    return calls


def upload(client, room_id: str, *, segment: int = 0, duration_ms: int = 8000, audio: bytes = AUDIO, started: str = "2026-09-20T10:00:00Z"):
    return client.post(
        f"/api/rooms/{room_id}/transcripts",
        files={"file": ("seg.webm", audio, "audio/webm")},
        data={"segmentIndex": str(segment), "startedAt": started, "durationMs": str(duration_ms)},
    )


# ---------- 纯函数 ----------

def test_stt_available_reflects_settings() -> None:
    """未配置 = base/key 任一为空；配置了就回模型名（前端据此禁用/启用开关）。"""
    base = load_settings()
    assert stt_service.stt_available(dataclasses.replace(base, stt_base_url="", stt_api_key="")) == (False, "")
    both = dataclasses.replace(base, stt_base_url="https://api.example.com/v1", stt_api_key="k")
    assert stt_service.stt_available(both) == (True, both.stt_model)
    assert stt_service.stt_available(dataclasses.replace(both, stt_api_key=""))[0] is False
    assert stt_service.estimate_segment_seconds(base) == base.stt_segment_seconds


# ---------- 权限与前置 ----------

def test_upload_requires_login(client, db) -> None:
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    client.cookies.clear()
    resp = upload(client, room["id"])
    assert resp.status_code == 401, resp.text


def test_upload_requires_active_membership(client, db) -> None:
    """非成员不能上传（403）；房间不存在 404。"""
    host = register_user(db, "房主")
    outsider = register_user(db, "外人")
    login(client, host)
    room = create_room(client)

    login(client, outsider)
    assert upload(client, room["id"]).status_code == 403
    assert upload(client, "room_不存在").status_code == 404


def test_upload_after_room_ended_returns_409_and_stays_readable(client, db, monkeypatch) -> None:
    """结束后不可再传（409 ROOM_ENDED），但已落的转写仍可读（只读可查，进纪要）。"""
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    stub_stt(monkeypatch, "结束前的最后一句")
    assert upload(client, room["id"]).status_code == 201

    assert client.post(f"/api/rooms/{room['id']}/end").status_code == 200
    resp = upload(client, room["id"], segment=1)
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "ROOM_ENDED"

    listed = client.get(f"/api/rooms/{room['id']}/transcripts")
    assert listed.status_code == 200, listed.text
    assert [item["text"] for item in listed.json()["data"]["transcripts"]] == ["结束前的最后一句"]


# ---------- 未配置 / 失败分支 ----------

def test_not_configured_returns_503_and_keeps_no_row(client, db, monkeypatch) -> None:
    """未配置 STT → 503 STT_NOT_CONFIGURED，且**不落库**（不伪装成功）。"""
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)

    bare = dataclasses.replace(load_settings(), stt_base_url="", stt_api_key="")
    monkeypatch.setattr(transcripts_service, "load_settings", lambda: bare)
    resp = upload(client, room["id"])
    assert resp.status_code == 503, resp.text
    assert resp.json()["error"]["code"] == "STT_NOT_CONFIGURED"
    cur = db.execute("SELECT count(*) FROM transcripts WHERE room_id = %s", (room["id"],))
    assert cur.fetchone()[0] == 0


def test_stt_failure_returns_502_and_keeps_no_row(client, db, monkeypatch) -> None:
    """STT 调用失败 → 502 STT_FAILED，不落库（客户端丢段继续，不阻塞对话）。"""
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)

    configured = dataclasses.replace(
        load_settings(), stt_base_url="https://stt.example.com/v1", stt_api_key="test-key"
    )
    monkeypatch.setattr(transcripts_service, "load_settings", lambda: configured)

    def boom(audio, *, filename, language=None, client=None, settings=None):
        raise stt_service.SttError("模拟超时")

    monkeypatch.setattr(stt_service, "call_stt", boom)
    resp = upload(client, room["id"])
    assert resp.status_code == 502, resp.text
    assert resp.json()["error"]["code"] == "STT_FAILED"
    cur = db.execute("SELECT count(*) FROM transcripts WHERE room_id = %s", (room["id"],))
    assert cur.fetchone()[0] == 0


def test_empty_text_from_stt_is_502(client, db, monkeypatch) -> None:
    """空文本也算失败（不落空行）。"""
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    stub_stt(monkeypatch, "   ")
    assert upload(client, room["id"]).status_code == 502


# ---------- 成功与幂等（E2/E3） ----------

def test_upload_success_writes_row_with_speaker_name(client, db, monkeypatch) -> None:
    """成功 → 201，返回文本 + 说话人（本人）+ 段落元数据；落库 1 行。"""
    host = register_user(db, "说话的人")
    login(client, host)
    room = create_room(client)
    calls = stub_stt(monkeypatch, "今天先聊第一章")

    resp = upload(client, room["id"], duration_ms=8000)
    assert resp.status_code == 201, resp.text
    body = resp.json()["data"]
    assert body["text"] == "今天先聊第一章"
    assert body["speakerId"] == host.id and body["speakerName"] == "说话的人"
    assert body["segmentIndex"] == 0 and body["durationMs"] == 8000
    assert body["final"] is True and body["language"] == "zh"
    assert len(calls) == 1 and calls[0]["bytes"] == len(AUDIO)

    cur = db.execute("SELECT count(*) FROM transcripts WHERE room_id = %s", (room["id"],))
    assert cur.fetchone()[0] == 1


def test_same_segment_is_idempotent_and_skips_stt(client, db, monkeypatch) -> None:
    """同一段重传 → 不新增行、不重复调 STT（省钱），返回已存在的那条。"""
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    calls = stub_stt(monkeypatch, "第一版")

    assert upload(client, room["id"], segment=0).status_code == 201
    again = upload(client, room["id"], segment=0)
    assert again.status_code == 201, again.text
    assert again.json()["data"]["text"] == "第一版"
    assert len(calls) == 1, "重传同段不应再次调用 STT"
    cur = db.execute("SELECT count(*) FROM transcripts WHERE room_id = %s", (room["id"],))
    assert cur.fetchone()[0] == 1

    # 下一段照常落库
    assert upload(client, room["id"], segment=1).status_code == 201
    cur = db.execute("SELECT count(*) FROM transcripts WHERE room_id = %s", (room["id"],))
    assert cur.fetchone()[0] == 2


def test_two_speakers_can_use_same_segment_index(client, db, monkeypatch) -> None:
    """幂等键含说话人：两个人各自的第 0 段互不冲突。"""
    host = register_user(db, "房主")
    member = register_user(db, "成员")
    login(client, host)
    room = create_room(client)
    add_member(db, room["id"], member.id)
    stub_stt(monkeypatch, "同一段号，不同的人")

    assert upload(client, room["id"], segment=0).status_code == 201
    login(client, member)
    assert upload(client, room["id"], segment=0).status_code == 201
    cur = db.execute("SELECT count(DISTINCT speaker_id) FROM transcripts WHERE room_id = %s", (room["id"],))
    assert cur.fetchone()[0] == 2


# ---------- 参数校验 ----------

def test_limits_and_bad_time_are_rejected(client, db, monkeypatch) -> None:
    """单段时长超上限 → 400；startedAt 非法 → 400（都在调 STT 之前拦下）。"""
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    stub_stt(monkeypatch)

    too_long = upload(client, room["id"], duration_ms=load_settings().stt_max_seconds * 1000 + 1)
    assert too_long.status_code == 400, too_long.text
    assert too_long.json()["error"]["code"] == "VALIDATION"

    bad_time = upload(client, room["id"], started="不是时间")
    assert bad_time.status_code == 400, bad_time.text


def test_audio_oversize_is_400(client, db, monkeypatch) -> None:
    """音频超体积上限 → 400（在调 STT 之前拦下；这里把上限调到 16 字节）。"""
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)

    tiny = dataclasses.replace(load_settings(), stt_max_bytes=16)
    monkeypatch.setattr(transcripts_service, "load_settings", lambda: tiny)
    too_big = upload(client, room["id"], audio=b"x" * 32)
    assert too_big.status_code == 400, too_big.text
    assert too_big.json()["error"]["code"] == "VALIDATION"


def test_list_limit_out_of_range_is_400(client, db, monkeypatch) -> None:
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    stub_stt(monkeypatch)
    assert upload(client, room["id"]).status_code == 201
    assert client.get(f"/api/rooms/{room['id']}/transcripts?limit=999").status_code == 400
    assert client.get(f"/api/rooms/{room['id']}/transcripts?limit=1").status_code == 200


def test_list_visibility_member_and_outsider(client, db, monkeypatch) -> None:
    """本房成员（含已离开）可读；非成员 403。"""
    host = register_user(db, "房主")
    gone = register_user(db, "离开的人")
    outsider = register_user(db, "外人")
    login(client, host)
    room = create_room(client)
    add_member(db, room["id"], gone.id)
    stub_stt(monkeypatch, "我走了但话还在")
    login(client, gone)
    assert upload(client, room["id"], segment=0).status_code == 201
    db.execute(
        """UPDATE room_members SET status = 'inactive', exit_reason = 'self_leave', left_at = now()
           WHERE room_id = %s AND user_id = %s""",
        (room["id"], gone.id),
    )

    login(client, gone)
    listed = client.get(f"/api/rooms/{room['id']}/transcripts")
    assert listed.status_code == 200
    assert listed.json()["data"]["transcripts"][0]["text"] == "我走了但话还在"

    login(client, outsider)
    assert client.get(f"/api/rooms/{room['id']}/transcripts").status_code == 403


def test_order_is_by_started_at_asc(client, db, monkeypatch) -> None:
    """列表按 started_at 正序（前端直接渲染）。"""
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    stub_stt(monkeypatch, "顺")
    assert upload(client, room["id"], segment=0, started="2026-09-20T10:00:05Z").status_code == 201
    assert upload(client, room["id"], segment=1, started="2026-09-20T10:00:01Z").status_code == 201
    listed = client.get(f"/api/rooms/{room['id']}/transcripts").json()["data"]["transcripts"]
    assert [item["segmentIndex"] for item in listed] == [1, 0]
