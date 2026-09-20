"""pytest 公共夹具：真实数据库连接。

约定：schema/服务/接口用例都跑真实 PostgreSQL（库 learning_guide，见 README）；`.env` 缺 DATABASE_URL
或数据库连不上时，只跳过**需要数据库**的用例并打印原因，纯函数用例照常执行。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api.errors import AppError  # noqa: E402
from app.config import load_settings  # noqa: E402
from app.db.pool import close_pool, get_conn, init_pool  # noqa: E402


@pytest.fixture(scope="session")
def settings():
    try:
        return load_settings()
    except AppError as exc:
        pytest.skip(f"需要数据库的用例已跳过：{exc.code} {exc.message}", allow_module_level=False)


@pytest.fixture(scope="session")
def pool(settings):
    try:
        init_pool(settings.database_url)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"需要数据库的用例已跳过：连接失败（{type(exc).__name__}）——检查 PostgreSQL 服务与 .env 的 DATABASE_URL")
    yield
    close_pool()


@pytest.fixture()
def db(pool):
    """借一条连接，整用例包在一个必定回滚的事务里（不污染种子数据）。"""
    with get_conn() as conn:
        with conn.transaction(force_rollback=True):
            yield conn


@pytest.fixture(autouse=True)
def _no_livekit_dispatch(monkeypatch):
    """r010：建房会派单转写 worker（`livekit.ensure_transcriber`）——用例一律桩掉，**零外部调用、零配额**。

    需要验证"确实调用了派单"的用例自行 `monkeypatch` 覆盖本桩（见 `test_transcript_segments.py`）。
    """
    from app.services import livekit as livekit_service

    monkeypatch.setattr(livekit_service, "ensure_transcriber", lambda *a, **k: "stub")
    yield


@pytest.fixture()
def client(db):
    """TestClient：把 `db_conn` 依赖覆盖成测试事务里的那条连接。

    这样接口层用例的写入也落在同一个「必定回滚」的事务里，不污染种子数据；
    不使用 `with TestClient(...)` 是为了跳过 lifespan 的关闭钩子（否则会把会话级连接池关掉）。
    """
    from fastapi.testclient import TestClient

    from app.api.deps import db_conn as real_db_conn
    from app.main import create_app

    app = create_app()
    app.dependency_overrides[real_db_conn] = _override_with(db)
    return TestClient(app)


def _override_with(db):
    """把依赖替换成"返回同一测试连接"的生成器函数。"""

    def _dependency():
        yield db

    return _dependency


@pytest.fixture()
def protected(db):
    """仅测试用的最小受保护路由：验证 401/放行两条路径（避免为测试往生产代码加路由）。"""
    from fastapi import Depends, FastAPI
    from fastapi.testclient import TestClient

    from app.api.deps import current_user, db_conn
    from app.api.envelope import ok
    from app.api.errors import register_error_handlers

    app = FastAPI()
    register_error_handlers(app)

    @app.get("/api/_protected")
    def _protected(user=Depends(current_user)):
        return ok({"uid": user.id})

    app.dependency_overrides[db_conn] = _override_with(db)
    return TestClient(app)
