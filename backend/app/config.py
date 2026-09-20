"""进程环境读取处（全仓唯一）。

设计事实源：docs/01-architecture/r001-app-architecture.md §5（键表）、§9.1（签名）、§13
纪律：除本模块外任何地方不得直接读 `os.environ`；缺必填项一律启动即失败（CONFIG_MISSING），
      不允许"默认密钥"兜底；错误信息只报键名，不回显值（值可能含密钥）。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from app.api.errors import ERR_CONFIG_MISSING, AppError

APP_DIR = Path(__file__).resolve().parent          # backend/app
BACKEND_DIR = APP_DIR.parent                        # backend
REPO_ROOT = BACKEND_DIR.parent                      # 仓库根
ENV_FILE = REPO_ROOT / ".env"

DEFAULT_APP_ENV = "dev"
DEFAULT_ROOM_CAPACITY = 8
VALID_APP_ENVS = ("dev", "demo")
MIN_SESSION_SECRET_LEN = 32

# LiveKit（r002）：TTL 与超时由模式派生（单点可调，见 docs/02-modules/r002-livekit.md §6.1）
VALID_LIVEKIT_MODES = ("cloud", "self")
LIVEKIT_TOKEN_TTL_SECONDS = {"cloud": 3600, "self": 300}
DEFAULT_LIVEKIT_TIMEOUT_SECONDS = 10


@dataclass(frozen=True)
class Settings:
    """启动期唯一配置对象；`livekit_*` / `llm_*` 在 r001 允许为空（M2/M4 起填）。"""

    database_url: str
    session_secret: str
    app_env: str = DEFAULT_APP_ENV
    cors_origins: tuple[str, ...] = field(default_factory=tuple)
    room_capacity: int = DEFAULT_ROOM_CAPACITY
    # r008：限时邀请的有效期上限（秒）——用户口径「最长 1 分钟」，改这里一个数即可
    invite_ttl_max_seconds: int = 60
    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""
    livekit_mode: str = "cloud"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""

    @property
    def is_demo(self) -> bool:
        """演示环境：Cookie 加 Secure、由后端托管前端静态产物。"""
        return self.app_env == "demo"

    @property
    def livekit_token_ttl_seconds(self) -> int:
        """进房 Token 的有效期（秒）：cloud 3600 / self 300（ADR-0011 条 3，下限 60 秒）。"""
        return LIVEKIT_TOKEN_TTL_SECONDS.get(self.livekit_mode, LIVEKIT_TOKEN_TTL_SECONDS["cloud"])

    @property
    def livekit_timeout_seconds(self) -> int:
        """LiveKit 管控调用的超时（秒）。"""
        return DEFAULT_LIVEKIT_TIMEOUT_SECONDS


def require_env(name: str, default: Optional[str] = None) -> str:
    """读单个环境变量；无默认值且缺失/为空 → AppError(CONFIG_MISSING, 500)。"""
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        if default is not None:
            return default
        raise AppError(ERR_CONFIG_MISSING, f"缺少环境变量 {name}（见 .env.example）", status=500)
    return value


def _optional_env(name: str, default: str = "") -> str:
    value = os.environ.get(name)
    return default if value is None or value.strip() == "" else value.strip()


def _cors_origins() -> tuple[str, ...]:
    """`CORS_ORIGINS` 逗号分隔；开发走 Vite 代理、演示走同源，默认空即不放开 CORS（§6）。"""
    raw = _optional_env("CORS_ORIGINS")
    return tuple(item.strip() for item in raw.split(",") if item.strip())


def validate_startup(s: Settings) -> None:
    """校验必填与取值；失败即抛 CONFIG_MISSING（进程退出，不做降级）。"""
    if s.app_env not in VALID_APP_ENVS:
        raise AppError(ERR_CONFIG_MISSING, f"APP_ENV 只能是 {'/'.join(VALID_APP_ENVS)}", status=500)
    if len(s.session_secret) < MIN_SESSION_SECRET_LEN:
        raise AppError(
            ERR_CONFIG_MISSING,
            f"SESSION_SECRET 太短（至少 {MIN_SESSION_SECRET_LEN} 字符，建议 32 字节 hex）",
            status=500,
        )
    if not (2 <= s.room_capacity <= DEFAULT_ROOM_CAPACITY):
        raise AppError(ERR_CONFIG_MISSING, f"ROOM_CAPACITY 必须在 2~{DEFAULT_ROOM_CAPACITY} 之间", status=500)
    if not (10 <= s.invite_ttl_max_seconds <= 86400):
        raise AppError(ERR_CONFIG_MISSING, "INVITE_TTL_MAX_SECONDS 必须在 10~86400 秒之间", status=500)
    if not s.database_url.startswith("postgresql://"):
        raise AppError(ERR_CONFIG_MISSING, "DATABASE_URL 必须是 postgresql:// 连接串", status=500)
    # r002 起：实时房间是核心能力，LiveKit 三项必填（只报键名，不回显值）
    if s.livekit_mode not in VALID_LIVEKIT_MODES:
        raise AppError(ERR_CONFIG_MISSING, f"LIVEKIT_MODE 只能是 {'/'.join(VALID_LIVEKIT_MODES)}", status=500)
    for _key, _value in (("LIVEKIT_URL", s.livekit_url), ("LIVEKIT_API_KEY", s.livekit_api_key), ("LIVEKIT_API_SECRET", s.livekit_api_secret)):
        if not _value:
            raise AppError(ERR_CONFIG_MISSING, f"缺少环境变量 {_key}（见 .env.example）", status=500)
    if not (s.livekit_url.startswith("wss://") or s.livekit_url.startswith("ws://")):
        raise AppError(ERR_CONFIG_MISSING, "LIVEKIT_URL 必须是 ws:// 或 wss:// 地址", status=500)


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    """读 `.env`（不覆盖已存在的进程环境变量）并组装 Settings；进程内缓存。"""
    load_dotenv(ENV_FILE, override=False)
    try:
        capacity = int(require_env("ROOM_CAPACITY", str(DEFAULT_ROOM_CAPACITY)))
    except ValueError as exc:  # 非数字
        raise AppError(ERR_CONFIG_MISSING, "ROOM_CAPACITY 必须是整数", status=500) from exc
    settings = Settings(
        database_url=require_env("DATABASE_URL"),
        session_secret=require_env("SESSION_SECRET"),
        app_env=require_env("APP_ENV", DEFAULT_APP_ENV),
        cors_origins=_cors_origins(),
        room_capacity=capacity,
        invite_ttl_max_seconds=int(require_env("INVITE_TTL_MAX_SECONDS", "60")),
        livekit_url=_optional_env("LIVEKIT_URL"),
        livekit_api_key=_optional_env("LIVEKIT_API_KEY"),
        livekit_api_secret=_optional_env("LIVEKIT_API_SECRET"),
        livekit_mode=_optional_env("LIVEKIT_MODE", "cloud"),
        llm_base_url=_optional_env("LLM_BASE_URL"),
        llm_api_key=_optional_env("LLM_API_KEY"),
        llm_model=_optional_env("LLM_MODEL"),
    )
    validate_startup(settings)
    return settings


def reset_settings_cache() -> None:
    """测试用：清掉 Settings 缓存（换 .env 后重新加载）。"""
    load_settings.cache_clear()
