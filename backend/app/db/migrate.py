"""迁移与种子（前进式 + 版本表）。

设计事实源：docs/01-architecture/r001-app-architecture.md §7；docs/02-modules/r001-rooms.md §6.2
- `sql/*.sql` 按文件名顺序执行；已记入 `schema_migrations` 的版本跳过；
- 每个版本在单事务内执行（PostgreSQL 支持事务性 DDL）；
- `reset_schema` 只在显式 `--reset` 时 DROP；`seed` 用固定 ID + ON CONFLICT DO NOTHING 保证幂等。
"""
from __future__ import annotations

from pathlib import Path

from psycopg import Connection

SQL_DIR = Path(__file__).resolve().parent / "sql"

VERSION_TABLE = "schema_migrations"
# 建表顺序无关（reset 用 CASCADE），清单与 001_schema.sql 一致，供 table_counts/reset_schema 使用。
BUSINESS_TABLES = ("users", "rooms", "room_members", "join_requests", "invites", "chat_messages")
COUNTED_TABLES = (VERSION_TABLE,) + BUSINESS_TABLES


def sql_files() -> list[Path]:
    """`sql/` 下的迁移文件，按文件名升序（001_ → 002_ …）。"""
    return sorted(SQL_DIR.glob("*.sql"))


def split_statements(sql: str) -> list[str]:
    """把迁移脚本切成单条语句。

    只需处理本项目用到的语法：`--` 行注释、`/* */` 块注释、单引号字符串（`''` 转义）、
    `$tag$ ... $tag$` 美元引用。这样迁移文件里可以自由写注释与字符串字面量，
    不必依赖驱动是否允许「一次执行多语句」。
    """
    statements: list[str] = []
    buf: list[str] = []
    i, n = 0, len(sql)
    while i < n:
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < n else ""
        if ch == "-" and nxt == "-":                      # 行注释
            while i < n and sql[i] != "\n":
                i += 1
            continue
        if ch == "/" and nxt == "*":                      # 块注释
            end = sql.find("*/", i + 2)
            i = n if end == -1 else end + 2
            continue
        if ch == "'":                                     # 单引号字符串
            buf.append(ch)
            i += 1
            while i < n:
                buf.append(sql[i])
                if sql[i] == "'":
                    if i + 1 < n and sql[i + 1] == "'":   # '' 转义
                        buf.append(sql[i + 1])
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            continue
        if ch == "$":                                     # 美元引用
            tag_end = sql.find("$", i + 1)
            tag = sql[i : tag_end + 1] if tag_end != -1 else ""
            if tag and all(c.isalnum() or c == "_" for c in tag[1:-1]):
                close = sql.find(tag, tag_end + 1)
                if close != -1:
                    buf.append(sql[i : close + len(tag)])
                    i = close + len(tag)
                    continue
        if ch == ";":                                     # 语句结束
            statement = "".join(buf).strip()
            if statement:
                statements.append(statement)
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        statements.append(tail)
    return statements


def _applied_versions(conn: Connection) -> set[str]:
    """已应用版本；版本表还没建时返回空集（首次迁移）。"""
    exists = conn.execute("SELECT to_regclass(%s) IS NOT NULL", (VERSION_TABLE,)).fetchone()[0]
    if not exists:
        return set()
    rows = conn.execute(f"SELECT version FROM {VERSION_TABLE}").fetchall()
    return {row[0] for row in rows}


def run_migrations(conn: Connection) -> list[str]:
    """执行未应用的迁移，返回本次应用的版本名列表。"""
    applied = _applied_versions(conn)
    done: list[str] = []
    for path in sql_files():
        version = path.stem
        if version in applied:
            continue
        statements = split_statements(path.read_text(encoding="utf-8"))
        if not statements:
            continue
        with conn.transaction():
            for statement in statements:
                conn.execute(statement)
            conn.execute(
                f"INSERT INTO {VERSION_TABLE} (version) VALUES (%s) ON CONFLICT DO NOTHING", (version,)
            )
        done.append(version)
    return done


def reset_schema(conn: Connection) -> None:
    """DROP 全部业务表（含版本表），仅 `--reset` 显式调用。"""
    with conn.transaction():
        for table in COUNTED_TABLES:
            conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")


def seed(conn: Connection) -> dict[str, int]:
    """执行 002_seed.sql（幂等），返回各表行数。"""
    path = SQL_DIR / "002_seed.sql"
    statements = split_statements(path.read_text(encoding="utf-8"))
    with conn.transaction():
        for statement in statements:
            conn.execute(statement)
    return table_counts(conn)


def table_counts(conn: Connection) -> dict[str, int]:
    """各表 `count(*)`（`db_init` 的证据输出）。"""
    counts: dict[str, int] = {}
    for table in COUNTED_TABLES:
        counts[table] = conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
    return counts
