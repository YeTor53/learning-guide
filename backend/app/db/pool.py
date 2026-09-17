"""连接池生命周期（进程级单例）。

设计事实源：docs/01-architecture/r001-app-architecture.md §7、§9.3；docs/02-modules/r001-rooms.md §6.1
约定：每请求借一条连接（`autocommit=False`）；写操作由 service 层显式 `with conn.transaction():`；
      连接正常退出即提交、异常退出即回滚（psycopg_pool 语义）。
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Optional

from psycopg import Connection
from psycopg_pool import ConnectionPool

_pool: Optional[ConnectionPool] = None


def init_pool(dsn: str, min_size: int = 1, max_size: int = 8) -> None:
    """建连接池（重复调用直接返回；测试换库前先 close_pool）。"""
    global _pool
    if _pool is not None:
        return
    _pool = ConnectionPool(conninfo=dsn, min_size=min_size, max_size=max_size, open=False)
    _pool.open(wait=True, timeout=10)


def get_pool() -> ConnectionPool:
    if _pool is None:
        raise RuntimeError("连接池未初始化：请先调用 init_pool(dsn)")
    return _pool


@contextmanager
def get_conn() -> Iterator[Connection]:
    """上下文管理器：借/还连接（正常提交、异常回滚）。"""
    with get_pool().connection() as conn:
        yield conn


def close_pool() -> None:
    """关池（脚本与测试收尾；下次 init_pool 会重建）。"""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
