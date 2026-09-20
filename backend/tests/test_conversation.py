"""r010 三源合一用例（离线，零配额）：聊天 + 系统消息 + 语音转写合成一条时间正序的对话流。

设计事实源：`docs/rounds/r010-transcription/design.md` §9.5（R2/R3：说的话并入文字对话，且与管理信息同流）。
"""
from __future__ import annotations

from helpers import register_user, session_cookie

TOPIC = {"topic": "custom", "topicLabel": "转写", "title": "对话流房", "description": ""}


def login(client, user) -> None:
    name, value = session_cookie(user.id)
    client.cookies.set(name, value)


def create_room(client) -> dict:
    resp = client.post("/api/rooms", json=TOPIC)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def add_member(db, room_id: str, user_id: str, role: str = "participant") -> None:
    db.execute(
        "INSERT INTO room_members (id, room_id, user_id, role) VALUES (%s, %s, %s, %s)",
        (f"mem_{user_id[-6:]}", room_id, user_id, role),
    )


def post_segment(client, room_id: str, *, speaker: str, seg: str, text: str, started: str, duration: int = 2000):
    return client.post(
        f"/api/rooms/{room_id}/transcripts/segments",
        json={
            "externalId": seg,
            "speakerIdentity": speaker,
            "text": text,
            "startedAt": started,
            "durationMs": duration,
            "language": "zh",
            "final": True,
        },
    )


def test_conversation_merges_three_sources_in_time_order(client, db) -> None:
    """三源（系统 / 聊天 / 语音）按时间正序合并，字段齐（speaker / durationMs / externalId）。"""
    host = register_user(db, "房主")
    mate = register_user(db, "同学")
    login(client, host)
    room = create_room(client)

    # 系统消息：让 mate 走真实等候室流程加入（批准后 r005 会写一条房间事件；同时他也就成了在册成员）
    login(client, mate)
    req = client.post(f"/api/rooms/{room['id']}/join-requests", json={"message": ""}).json()["data"]
    login(client, host)
    assert client.post(f"/api/join-requests/{req['id']}/approve").status_code == 200

    # 聊天消息
    assert client.post(f"/api/rooms/{room['id']}/messages", json={"body": "我们先看看第一章"}).status_code == 201

    # 语音转写（两条，验证排序用 startedAt 而不是入库顺序）
    assert post_segment(client, room["id"], speaker=mate.id, seg="SG_c1", text="这是第二句", started="2026-09-20T10:00:05Z").status_code == 201
    assert post_segment(client, room["id"], speaker=host.id, seg="SG_c2", text="这是第一句", started="2026-09-20T10:00:01Z").status_code == 201

    resp = client.get(f"/api/rooms/{room['id']}/conversation")
    assert resp.status_code == 200, resp.text
    items = resp.json()["data"]["items"]

    kinds = [item["kind"] for item in items]
    assert kinds.count("speech") == 2
    assert "chat" in kinds and "system" in kinds, kinds

    speech = [item for item in items if item["kind"] == "speech"]
    assert [item["text"] for item in speech] == ["这是第一句", "这是第二句"], "按 startedAt 正序"
    first = speech[0]
    assert first["speakerId"] == host.id and first["speakerName"] == "房主"
    assert first["meta"]["durationMs"] == 2000 and first["meta"]["externalId"] == "SG_c2"

    ats = [item["at"] for item in items]
    assert ats == sorted(ats), "整条流按时间正序"


def test_conversation_visibility_and_limit(client, db) -> None:
    host = register_user(db, "房主")
    gone = register_user(db, "离开的人")
    outsider = register_user(db, "外人")
    login(client, host)
    room = create_room(client)
    add_member(db, room["id"], gone.id)
    assert post_segment(client, room["id"], speaker=gone.id, seg="SG_v1", text="我走了话还在", started="2026-09-20T10:00:00Z").status_code == 201
    db.execute(
        """UPDATE room_members SET status = 'inactive', exit_reason = 'self_leave', left_at = now()
           WHERE room_id = %s AND user_id = %s""",
        (room["id"], gone.id),
    )

    login(client, gone)
    assert client.get(f"/api/rooms/{room['id']}/conversation").status_code == 200

    login(client, outsider)
    assert client.get(f"/api/rooms/{room['id']}/conversation").status_code == 403

    client.cookies.clear()
    assert client.get(f"/api/rooms/{room['id']}/conversation").status_code == 401

    login(client, host)
    assert client.get(f"/api/rooms/{room['id']}/conversation?limit=999").status_code == 400


def test_conversation_readable_after_room_ended(client, db) -> None:
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    assert post_segment(client, room["id"], speaker=host.id, seg="SG_e1", text="结束前留一句", started="2026-09-20T10:00:00Z").status_code == 201
    assert client.post(f"/api/rooms/{room['id']}/end").status_code == 200

    resp = client.get(f"/api/rooms/{room['id']}/conversation")
    assert resp.status_code == 200, resp.text
    assert any(item["text"] == "结束前留一句" for item in resp.json()["data"]["items"])
