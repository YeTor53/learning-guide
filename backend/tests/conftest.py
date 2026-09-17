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
