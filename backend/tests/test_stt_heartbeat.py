"""r011 用例：转写 worker 心跳（`POST /api/stt/heartbeat` + `/rooms/{id}/stt-status`）。

零网络、零配额：只打自己的后端接口，不碰 LiveKit 与 STT 服务。
"""
from __future__ import annotations

from helpers import register_user, session_cookie

TOPIC = {"topic": "custom", "topicLabel": "心跳", "title": "心跳房", "description": ""}


def login(client, user) -> None:
    name, value = session_cookie(user.id)
    client.cookies.set(name, value)


def create_room(client) -> dict:
    resp = client.post("/api/rooms", json=TOPIC)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def test_heartbeat_rejects_missing_or_bad_token(client, db) -> None:
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    body = {"roomId": room["id"], "workerId": "w-test", "sessions": 1}
    assert client.post("/api/stt/heartbeat", json=body).status_code == 401
    bad = client.post("/api/stt/heartbeat", json=body, headers={"X-Agent-Token": "deadbeef"})
    assert bad.status_code == 401
    assert bad.json()["error"]["code"] == "UNAUTHORIZED"


def test_heartbeat_shows_up_in_room_status(client, db) -> None:
    from app.api.routers.transcripts import agent_heartbeat_token
    from app.config import load_settings

    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    token = agent_heartbeat_token(room["id"], load_settings().session_secret)

    body = {"roomId": room["id"], "workerId": "w-test", "sessions": 2}
    ok = client.post("/api/stt/heartbeat", json=body, headers={"X-Agent-Token": token})
    assert ok.status_code == 200, ok.text

    data = client.get(f"/api/rooms/{room['id']}/stt-status").json()["data"]
    assert data["workerId"] == "w-test"
    assert data["sessions"] == 2
    assert data["lastHeartbeatAt"] is not None
    assert data["heartbeatAgeSeconds"] is not None and data["heartbeatAgeSeconds"] < 5
    assert data["fresh"] is True

    # 全局状态也带上最近一次心跳（向后兼容：老前端只读 mode）
    global_status = client.get("/api/stt/status").json()["data"]
    assert global_status["lastHeartbeatRoomId"] == room["id"]
    assert global_status["lastHeartbeatAt"] is not None


def test_room_without_heartbeat_reports_null(client, db) -> None:
    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    data = client.get(f"/api/rooms/{room['id']}/stt-status").json()["data"]
    assert data["lastHeartbeatAt"] is None
    assert data["heartbeatAgeSeconds"] is None
    assert data["fresh"] is False


def test_heartbeat_carries_last_error_to_room_status(client, db) -> None:
    """r013：worker 上报的 `lastError` 要能从 `/rooms/{id}/stt-status` 读回来（控制坞芯片 hover 用）。"""
    from app.api.routers.transcripts import agent_heartbeat_token
    from app.config import load_settings

    host = register_user(db, "房主")
    login(client, host)
    room = create_room(client)
    token = agent_heartbeat_token(room["id"], load_settings().session_secret)

    body = {
        "roomId": room["id"],
        "workerId": "w-test",
        "sessions": 0,
        "lastError": "连接失败（3 次）：APIConnectionError: timed out waiting for ReadyForRoomEventRequest",
    }
    ok = client.post("/api/stt/heartbeat", json=body, headers={"X-Agent-Token": token})
    assert ok.status_code == 200

    status = client.get(f"/api/rooms/{room['id']}/stt-status")
    assert status.status_code == 200
    assert status.json()["data"]["lastError"] == body["lastError"]

    # 不带 lastError 的心跳要把上次的错误清掉（否则前端会一直显示过期错误）
    body.pop("lastError")
    assert client.post("/api/stt/heartbeat", json=body, headers={"X-Agent-Token": token}).status_code == 200
    cleared = client.get(f"/api/rooms/{room['id']}/stt-status").json()["data"]
    assert cleared["lastError"] is None
