"""应用装配：路由、异常处理器、静态托管、生命周期。

设计事实源：docs/01-architecture/r001-app-architecture.md §9.2、§10、§13
启动顺序：`validate_startup`（缺必填项即退出）→ 建连接池；关闭时关池。
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.errors import register_error_handlers
from app.api.routers.auth import router as auth_router
from app.api.routers.room_extras import router as room_extras_router
from app.api.routers.rooms import router as rooms_router
from app.config import REPO_ROOT, load_settings, validate_startup
from app.db.pool import close_pool, init_pool

logger = logging.getLogger("app")
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = load_settings()
    validate_startup(settings)
    init_pool(settings.database_url)
    logger.info("后端就绪：APP_ENV=%s，数据库连接池已建立", settings.app_env)
    try:
        yield
    finally:
        close_pool()


def register_routers(app: FastAPI) -> None:
    app.include_router(auth_router, prefix="/api")
    app.include_router(rooms_router, prefix="/api")
    app.include_router(room_extras_router, prefix="/api")


def mount_spa(app: FastAPI, dist_dir: Path = FRONTEND_DIST) -> None:
    """`APP_ENV=demo` 时由后端托管前端产物（同源，Cookie 不跨域）。"""
    if not dist_dir.exists():
        logger.warning("未找到前端产物目录 %s：仅 API 可用（先 cd frontend && npm run build）", dist_dir)
        return
    index = dist_dir / "index.html"
    assets = dist_dir / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/", include_in_schema=False)
    def _index() -> FileResponse:
        return FileResponse(index)

    @app.get("/{full_path:path}", include_in_schema=False)
    def _spa_fallback(full_path: str) -> FileResponse:
        candidate = dist_dir / full_path
        return FileResponse(candidate if candidate.is_file() else index)


def create_app() -> FastAPI:
    settings = load_settings()  # 缺必填项会抛 CONFIG_MISSING，进程起不来（不允许默认密钥兜底）
    app = FastAPI(title="Learning Guide 学习讨论室", version="0.1.0", lifespan=lifespan)
    register_error_handlers(app)
    register_routers(app)
    if settings.is_demo:
        mount_spa(app)
    return app


app = create_app()
