"""r012 用例：超管身份（`users.role`）与提权路径。

口径来源：docs/rounds/r012-superadmin-console/design.md §2.1 / §2.5（Q1=1、Q15=1）。
说明：本文件只测身份与判据；「隐身进房 / 旁路治理」的用例在 cp-3 落地。
"""
from __future__ import annotations

import pytest

from helpers import register_user, session_cookie

from app.api.errors import AppError
from app.repositories import users as users_repo
from app.services import auth as auth_service
from app.services import roles
from app.services.roles import SUPERADMIN


def login(client, user) -> None:
    name, value = session_cookie(user.id)
    client.cookies.set(name, value)


def test_new_users_are_regular_by_default(client, db) -> None:
    user = register_user(db, "普通同学")
    assert user.role == "user"
    assert users_repo.get_user_by_id(db, user.id).role == "user"

    login(client, user)
    me = client.get("/api/auth/me").json()["data"]["user"]
    assert me["role"] == "user"      # camelCase 出参，前端据此显示入口


def test_promote_and_demote_writes_role_and_me_reflects_it(client, db) -> None:
    user = register_user(db, "被提权的同学")

    assert users_repo.set_user_role(db, user.id, SUPERADMIN) == 1
    assert users_repo.get_user_by_id(db, user.id).role == SUPERADMIN
    login(client, user)
    assert client.get("/api/auth/me").json()["data"]["user"]["role"] == SUPERADMIN

    assert users_repo.set_user_role(db, user.id, roles.USER) == 1
    assert client.get("/api/auth/me").json()["data"]["user"]["role"] == "user"


def test_set_user_role_reports_zero_rows_for_unknown_user(db) -> None:
    assert users_repo.set_user_role(db, "usr_not_exists", SUPERADMIN) == 0


def test_seed_demo_superadmin_uses_the_demo_password_account(db) -> None:
    """seed（012_r012_seed_superadmin.sql）写的演示超管：可登录、角色为 superadmin。"""
    from app.schemas.auth import LoginIn

    row = users_repo.get_user_by_email(db, "admin@example.com")
    assert row is not None, "演示超管账号缺失（先跑 python backend/scripts/db_init.py --seed）"
    assert row.role == SUPERADMIN
    assert auth_service.login(db, LoginIn(email="admin@example.com", password="demo1234")).id == row.id


def test_assert_superadmin_matrix(db) -> None:
    """未登录 401 / 普通用户 403 / 超管放行——管理后台端点的统一前置。"""
    with pytest.raises(AppError) as missing:
        roles.assert_superadmin(None)
    assert (missing.value.code, missing.value.status) == ("UNAUTHORIZED", 401)

    plain = register_user(db, "普通同学")
    with pytest.raises(AppError) as forbidden:
        roles.assert_superadmin(plain)
    assert (forbidden.value.code, forbidden.value.status) == ("FORBIDDEN", 403)

    users_repo.set_user_role(db, plain.id, SUPERADMIN)
    promoted = auth_service.get_user(db, plain.id)
    assert roles.is_superadmin(promoted) is True
    assert roles.assert_superadmin(promoted).id == plain.id
