"""r010 A 路径用例：前端回传转写段（离线，不触碰任何 STT 服务、零配额）。

设计事实源：`docs/rounds/r010-transcription/design.md` §9.3；决定见 ADR-0023。
口径：只落最终稿（`final=false` → 204 不落库）；幂等键 = 官方 segment.id；说话人 = LiveKit identity = `user_id`。
"""
from __future__ import annotations

import pytest

from helpers import register_user, session_cookie

TOPIC = {"topic": "custom", "topicLabel": "转写", "title": "转写房", "description": ""}
SEG = {
    "externalId": "SG_test0001",
    "text": "今天先讲第一章线性回归",
    "startedAt": "2026-09-20T10:00:00Z",
    "durationMs": 3200,
    "language": "zh",
    "final": True,
}


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


def upload(client, room_id: str, **overrides):
    body = {**SEG, "speakerIdentity": overrides.pop("speaker_identity", ""), **overrides}
    return client.post(f"/api/rooms/{room_id}/transcripts/segments", json=body)


def test_requires_login_and_membership(client, db) -> None:
    host = register_user(db, "房主")
    outsider = register_user(db, "外人")
    login(client, host)
    room = create_room(client)

    client.cookies.clear()
    assert upload(client, room["id"], speaker_identity=host.id).status_code == 401

    login(client, outsider)
    assert upload(client, room["id"], speaker_identity=host.id).status_code == 403

    # 房间不存在 → 404
    login(client, host)
    assert upload(client, "room_不存在", speaker_identity=host.id).status_code == 404


def test_speaker_must_be_room_member(client, db) -> None:
    """说话人必须是本房成员（含已离开）——防止把外人写进房间记录。"""
    host = register_user(db, "房主")
    outsider = register_user(db, "外人")
    login(client, host)
    room = create_room(client)

    resp = upload(client, room["id"], speaker_identity=outsider.id)
    assert resp.status_code == 400, resp.text
    assert resp.json()["error"]["code"] == "VALIDATION"


def test_success_then_idempotent_on_same_segment_id(client, db) -> None:
    """成功落库 1 行；同 segmentId 重复上报（多端冗余）→ created=false 且不新增行。"""
    host = register_user(db, "房主")
    speaker = register_user(db, "说话的人")
    login(client, host)
    room = create_room(client)
    add_member(db, room["id"], speaker.id)

    first = upload(client, room["id"], speaker_identity=speaker.id)
    assert first.status_code == 201, first.text
    data = first.json()["data"]
    assert data["created"] is True
    item = data["transcript"]
    assert item["text"] == SEG["text"]
    assert item["speakerId"] == speaker.id and item["speakerName"] == "说话的人"
    assert item["externalId"] == SEG["externalId"]
    assert item["segmentIndex"] is None, "A 路径没有本端分段序号"
    assert item["provider"] == "livekit" and item["model"], item
    assert item["durationMs"] == 3200

    again = upload(client, room["id"], speaker_identity=speaker.id)
    assert again.status_code == 201, again.text
    assert again.json()["data"]["created"] is False
    assert again.json()["data"]["transcript"]["id"] == item["id"]

    cur = db.execute("SELECT count(*), max(segment_index) FROM transcripts WHERE room_id = %s", (room["id"],))
    count, seg_index = cur.fetchone()
    assert count == 1 and seg_index is None


def test_interim_segment_is_dropped_with_204(client, db) -> None:
    """中间稿（final=false）不落库。"""
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)

    resp = upload(client, room["id"], speaker_identity=host.id, final=False, externalId="SG_interim1")
    assert resp.status_code == 204, resp.text
    cur = db.execute("SELECT count(*) FROM transcripts WHERE room_id = %s", (room["id"],))
    assert cur.fetchone()[0] == 0


def test_zero_duration_is_clamped_to_one(client, db) -> None:
    """真 STT 可能缺 startTime/endTime → durationMs=0 落库兜底为 1（表约束要求 > 0）。"""
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    resp = upload(client, room["id"], speaker_identity=host.id, durationMs=0, externalId="SG_zero1")
    assert resp.status_code == 201, resp.text
    assert resp.json()["data"]["transcript"]["durationMs"] == 1


def test_rejects_too_long_text_and_bad_time(client, db) -> None:
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    assert upload(client, room["id"], speaker_identity=host.id, text="字" * 2001).status_code == 400
    assert upload(client, room["id"], speaker_identity=host.id, startedAt="不是时间").status_code == 400


def test_after_room_ended_is_409_but_still_readable(client, db) -> None:
    """结束后不可再上报（409），但已落转写仍可读（进纪要）。"""
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    assert upload(client, room["id"], speaker_identity=host.id).status_code == 201
    assert client.post(f"/api/rooms/{room['id']}/end").status_code == 200

    resp = upload(client, room["id"], speaker_identity=host.id, externalId="SG_after_end")
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "ROOM_ENDED"

    listed = client.get(f"/api/rooms/{room['id']}/transcripts")
    assert listed.status_code == 200
    assert [x["text"] for x in listed.json()["data"]["transcripts"]] == [SEG["text"]]


def test_stt_status_reports_agent_mode(client, db) -> None:
    host = register_user(db, "房主")
    login(client, host)
    resp = client.get("/api/stt/status")
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["mode"] == "agent"
    assert data["agentName"] == "learning-guide-transcriber"
    assert data["maxSessions"] == 5


def test_create_room_dispatches_transcriber(client, db, monkeypatch) -> None:
    """建房时应触发一次 worker 派单（用 spy 覆盖 conftest 的自动桩，仍为零网络）。"""
    from app.services import livekit as livekit_service

    seen: list[str] = []
    monkeypatch.setattr(livekit_service, "ensure_transcriber", lambda room_id, settings=None: seen.append(room_id) or "stub")

    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    assert seen == [room["id"]], seen
