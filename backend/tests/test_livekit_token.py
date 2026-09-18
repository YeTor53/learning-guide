"""r002 纯函数与配置断言：Token 契约 + LiveKit 配置校验（不联网、不需要数据库）。

设计事实源：`docs/02-modules/r002-livekit.md` §6.1/§6.4/§9、ADR-0011 条 2/3/9。
"""
from __future__ import annotations

import base64
import json

import jwt
import pytest

from app.api.errors import ERR_CONFIG_MISSING, AppError
from app.config import Settings, validate_startup
from app.services import livekit

SECRET = "test_secret_do_not_use_in_prod_0123456789"
KEY = "APItestkey"


def make_settings(mode: str = "cloud", **overrides) -> Settings:
    base = dict(
        database_url="postgresql://u:p@127.0.0.1:5432/db",
        session_secret="x" * 48,
        app_env="dev",
        room_capacity=8,
        livekit_url="wss://example.livekit.cloud",
        livekit_api_key=KEY,
        livekit_api_secret=SECRET,
        livekit_mode=mode,
    )
    base.update(overrides)
    return Settings(**base)


def claims_of(token: str) -> dict:
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))


# ---------- Token 契约 ----------

def test_host_token_grants_and_room_config():
    s = make_settings()
    token = livekit.issue_token("room_demo_epicurus", "usr_demo_host", "林泽宇", "host", settings=s)
    c = claims_of(token)
    assert token.count(".") == 2
    assert c["sub"] == "usr_demo_host"
    assert c["name"] == "林泽宇"
    assert c["video"]["room"] == "room_demo_epicurus"
    assert c["video"]["roomJoin"] is True
    assert c["video"]["roomAdmin"] is True
    assert c["roomConfig"]["maxParticipants"] == 8


@pytest.mark.parametrize("role", ["moderator", "participant"])
def test_non_host_is_not_room_admin(role):
    token = livekit.issue_token("r1", "u1", "某人", role, settings=make_settings())
    c = claims_of(token)
    assert c["video"].get("roomAdmin", False) is False


def test_ttl_follows_mode():
    cloud = claims_of(livekit.issue_token("r1", "u1", "n", "participant", settings=make_settings("cloud")))
    assert cloud["exp"] - cloud["nbf"] == 3600
    self_hosted = claims_of(livekit.issue_token("r1", "u1", "n", "participant", settings=make_settings("self")))
    assert self_hosted["exp"] - self_hosted["nbf"] == 300
    # 显式覆盖
    custom = claims_of(livekit.issue_token("r1", "u1", "n", "participant", settings=make_settings(), ttl_seconds=90))
    assert custom["exp"] - custom["nbf"] == 90


def test_token_verifiable_by_secret_and_secret_not_embedded():
    token = livekit.issue_token("r1", "u1", "n", "participant", settings=make_settings())
    decoded = jwt.decode(token, SECRET, algorithms=["HS256"], options={"verify_aud": False})
    assert decoded["sub"] == "u1"
    assert SECRET not in token  # Secret 不得出现在返回值里
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(token, "wrong-secret", algorithms=["HS256"], options={"verify_aud": False})


def test_capacity_overridable():
    token = livekit.issue_token("r1", "u1", "n", "participant", settings=make_settings(), max_participants=3)
    assert claims_of(token)["roomConfig"]["maxParticipants"] == 3


# ---------- 配置校验 ----------

def test_validate_startup_requires_livekit_keys():
    for missing in ("livekit_url", "livekit_api_key", "livekit_api_secret"):
        with pytest.raises(AppError) as exc:
            validate_startup(make_settings(**{missing: ""}))
        assert exc.value.code == ERR_CONFIG_MISSING
        assert missing.upper().replace("LIVEKIT_", "LIVEKIT_") in exc.value.message


def test_validate_startup_rejects_bad_mode_and_url():
    with pytest.raises(AppError) as exc:
        validate_startup(make_settings(livekit_mode="localhost"))
    assert exc.value.code == ERR_CONFIG_MISSING
    with pytest.raises(AppError):
        validate_startup(make_settings(livekit_url="https://example.livekit.cloud"))


def test_derived_timeout_and_ttl_are_single_sourced():
    s = make_settings("self")
    assert s.livekit_token_ttl_seconds == 300
    assert s.livekit_timeout_seconds == 10
    assert make_settings("cloud").livekit_token_ttl_seconds == 3600
