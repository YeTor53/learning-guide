"""账户接口（路由薄壳：取依赖 → 调 service → 信封）。

设计事实源：docs/01-architecture/r001-app-architecture.md §6、§8、§9.5
路由表：POST /api/auth/register（201）、POST /api/auth/login、POST /api/auth/logout、GET /api/auth/me
约定：登录、注册成功即下发会话 Cookie；`/me` 未登录返回 200 + `{"user": null}`（前端用它判断首屏状态）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from psycopg import Connection

from app.api.deps import current_user_optional, db_conn
from app.api.envelope import ok
from app.config import load_settings
from app.schemas.auth import LoginIn, RegisterIn, UserVO
from app.security.session import clear_session_cookie, set_session_cookie
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_payload(user: UserVO | None) -> dict:
    return {"user": user.model_dump(mode="json") if user else None}


@router.post("/register", status_code=201)
def register(payload: RegisterIn, conn: Connection = Depends(db_conn)):
    settings = load_settings()
    user = auth_service.register(conn, payload)
    response = ok(_user_payload(user), status=201)
    set_session_cookie(response, user.id, settings.session_secret, settings.is_demo)
    return response


@router.post("/login", status_code=200)
def login(payload: LoginIn, conn: Connection = Depends(db_conn)):
    settings = load_settings()
    user = auth_service.login(conn, payload)
    response = ok(_user_payload(user), status=200)
    set_session_cookie(response, user.id, settings.session_secret, settings.is_demo)
    return response


@router.post("/logout", status_code=200)
def logout():
    """登出：只清 Cookie（无服务端吊销列表，见架构页 §6 的取舍说明）。"""
    response = ok(_user_payload(None), status=200)
    clear_session_cookie(response)
    return response


@router.get("/me", status_code=200)
def me(user: UserVO | None = Depends(current_user_optional)):
    return ok(_user_payload(user), status=200)
