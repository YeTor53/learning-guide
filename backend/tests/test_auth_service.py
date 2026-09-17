"""账户模块用例：口令/会话纯函数、服务层规则、接口层行为。

设计事实源：docs/00-requirements/r001-skeleton-accounts-rooms.md §3（验收清单·账户）、
            docs/01-architecture/r001-app-architecture.md §6/§8
"""
from __future__ import annotations

import time
from uuid import uuid4

import pytest

from app.api.errors import AppError
from app.schemas.auth import LoginIn, RegisterIn
from app.security.password import hash_password, verify_password
from app.security.session import read_session, sign_session
from app.services import auth as auth_service

PASSWORD = "demo-pass-123"


def _email() -> str:
    """每个用例用独立邮箱，避免与种子数据或其他用例相撞。"""
    return f"u{uuid4().hex[:10]}@example.com"


def _register(conn, email: str | None = None, password: str = PASSWORD, display_name: str = "测试同学"):
    return auth_service.register(conn, RegisterIn(email=email or _email(), display_name=display_name, password=password))


# ---------- 纯函数（不需要数据库） ----------

def test_password_hash_roundtrip() -> None:
    stored = hash_password(PASSWORD)
    assert stored.startswith("scrypt$16384$8$1$")
    assert PASSWORD not in stored
    assert verify_password(PASSWORD, stored) is True
    assert verify_password(PASSWORD + "x", stored) is False


def test_password_hash_uses_random_salt() -> None:
    assert hash_password(PASSWORD) != hash_password(PASSWORD)


def test_verify_password_rejects_malformed_hash() -> None:
    assert verify_password(PASSWORD, "plaintext") is False
    assert verify_password(PASSWORD, "scrypt$1$2$3$bad") is False
    assert verify_password(PASSWORD, "") is False


def test_session_sign_and_read_roundtrip() -> None:
    token = sign_session("usr_1", int(time.time()) + 60, "secret-key")
    assert read_session(token, "secret-key") == "usr_1"
    assert read_session(token, "other-key") is None
    assert read_session(token + "x", "secret-key") is None
    assert read_session("garbage", "secret-key") is None


def test_session_expiry() -> None:
    token = sign_session("usr_1", int(time.time()) - 1, "secret-key")
    assert read_session(token, "secret-key") is None


# ---------- 服务层（需要数据库） ----------

def test_register_writes_scrypt_hash_and_returns_vo(db) -> None:
    email = _email()
    user = _register(db, email)
    assert user.email == email
    assert user.id.startswith("usr_")
    stored = db.execute("SELECT password_hash FROM users WHERE id = %s", (user.id,)).fetchone()[0]
    assert stored.startswith("scrypt$")
    assert PASSWORD not in stored


def test_register_normalizes_email_case(db) -> None:
    user = _register(db, "MiXeD@Example.COM")
    assert user.email == "mixed@example.com"


def test_register_duplicate_email_case_insensitive(db) -> None:
    email = _email()
    _register(db, email)
    with pytest.raises(AppError) as exc:
        _register(db, email.upper())
    assert (exc.value.code, exc.value.status) == ("EMAIL_TAKEN", 409)


def test_login_with_seed_demo_account(db) -> None:
    """种子里的演示账号口令是 demo1234（验证 002_seed.sql 的哈希口径与 password.py 一致）。"""
    user = auth_service.login(db, LoginIn(email="host@example.com", password="demo1234"))
    assert user.display_name == "林泽宇"


def test_login_rejects_wrong_password_and_unknown_email(db) -> None:
    email = _email()
    _register(db, email)
    for payload in (LoginIn(email=email, password="wrong-pass-123"), LoginIn(email=_email(), password=PASSWORD)):
        with pytest.raises(AppError) as exc:
            auth_service.login(db, payload)
        assert (exc.value.code, exc.value.status) == ("INVALID_CREDENTIALS", 401)


def test_get_user_returns_none_for_unknown_id(db) -> None:
    assert auth_service.get_user(db, "usr_not_exists") is None


# ---------- 接口层（TestClient） ----------

def test_register_endpoint_sets_cookie_and_me_returns_user(client) -> None:
    email = _email()
    resp = client.post("/api/auth/register", json={"email": email, "display_name": "接口同学", "password": PASSWORD})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["ok"] is True and body["data"]["user"]["email"] == email
    assert "password" not in str(body) and "password_hash" not in str(body)
    assert body["data"]["user"]["displayName"] == "接口同学"  # 用户 VO 也是 camelCase
    assert resp.cookies.get("lg_session")

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["data"]["user"]["email"] == email


def test_register_endpoint_duplicate_returns_409(client) -> None:
    email = _email()
    payload = {"email": email, "display_name": "接口同学", "password": PASSWORD}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    dup = client.post("/api/auth/register", json=payload)
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "EMAIL_TAKEN"


def test_register_endpoint_validation_error_envelope(client) -> None:
    resp = client.post("/api/auth/register", json={"email": "not-an-email", "display_name": "", "password": "短"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "VALIDATION"


def test_login_endpoint_and_logout(client) -> None:
    email = _email()
    client.post("/api/auth/register", json={"email": email, "display_name": "接口同学", "password": PASSWORD})
    client.post("/api/auth/logout")

    assert client.post("/api/auth/login", json={"email": email, "password": PASSWORD}).status_code == 200
    bad = client.post("/api/auth/login", json={"email": email, "password": "wrong-pass-123"})
    assert bad.status_code == 401 and bad.json()["error"]["code"] == "INVALID_CREDENTIALS"

    out = client.post("/api/auth/logout")
    assert out.status_code == 200 and out.json()["data"]["user"] is None
    assert client.get("/api/auth/me").json()["data"]["user"] is None


def test_me_without_cookie_returns_null_user(client) -> None:
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "data": {"user": None}}


def test_protected_route_requires_login(protected) -> None:
    resp = protected.get("/api/_protected")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_protected_route_allows_logged_in_user(db, protected) -> None:
    from app.config import load_settings
    from app.security.session import COOKIE_NAME

    user = _register(db)
    protected.cookies.set(COOKIE_NAME, sign_session(user.id, int(time.time()) + 60, load_settings().session_secret))
    resp = protected.get("/api/_protected")
    assert resp.status_code == 200
    assert resp.json()["data"]["uid"] == user.id


def test_protected_route_rejects_tampered_session_cookie(db, protected) -> None:
    from app.config import load_settings
    from app.security.session import COOKIE_NAME

    user = _register(db)
    token = sign_session(user.id, int(time.time()) + 60, load_settings().session_secret) + "x"
    protected.cookies.set(COOKIE_NAME, token)
    assert protected.get("/api/_protected").status_code == 401
