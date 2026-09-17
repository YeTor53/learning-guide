"""会话票据：HMAC-SHA256 签名的 Cookie（标准库，零依赖）。

设计事实源：docs/01-architecture/r001-app-architecture.md §6（会话形态）、§9.4
票据 = base64url(JSON{uid, exp}) + "." + base64url(HMAC-SHA256(payload, SESSION_SECRET))
取舍：登出只清 Cookie，没有服务端吊销列表（如实写进设计说明的"安全与取舍"）。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Optional

from fastapi import Response

COOKIE_NAME = "lg_session"
SESSION_TTL_SECONDS = 7 * 24 * 3600


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def sign_session(uid: str, exp: int, secret: str) -> str:
    """签名会话票据；`exp` 为 Unix 秒级过期时间。"""
    payload = _b64encode(json.dumps({"uid": uid, "exp": int(exp)}, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(secret.encode("utf-8"), payload.encode("ascii"), hashlib.sha256).digest()
    return f"{payload}.{_b64encode(signature)}"


def read_session(token: str, secret: str) -> Optional[str]:
    """验签 + 过期校验 → `uid`；任何异常（格式/签名/过期）一律返回 None。"""
    if not token or "." not in token:
        return None
    payload, _, signature = token.partition(".")
    expected = hmac.new(secret.encode("utf-8"), payload.encode("ascii"), hashlib.sha256).digest()
    try:
        if not hmac.compare_digest(_b64decode(signature), expected):
            return None
        data = json.loads(_b64decode(payload))
    except (ValueError, TypeError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("uid"), str):
        return None
    if int(data.get("exp", 0)) < int(time.time()):
        return None
    return data["uid"]


def session_exp(now: Optional[int] = None) -> int:
    return int(now if now is not None else time.time()) + SESSION_TTL_SECONDS


def set_session_cookie(response: Response, uid: str, secret: str, secure: bool, now: Optional[int] = None) -> None:
    """写 `lg_session`：HttpOnly + SameSite=Lax + Path=/，7 天；`APP_ENV=demo` 时加 Secure。"""
    response.set_cookie(
        key=COOKIE_NAME,
        value=sign_session(uid, session_exp(now), secret),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        path="/",
        secure=secure,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, path="/")
