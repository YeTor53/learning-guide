"""数据层初始化：迁移 + 种子 + 行数取证。

用法（在仓库根目录执行，环境为 conda `learningguide`）：
  python backend/scripts/db_init.py                  # 迁移到最新 + 打印各表行数
  python backend/scripts/db_init.py --seed           # 迁移 + 写演示种子数据
  python backend/scripts/db_init.py --reset --seed   # DROP 全部业务表 → 迁移 → 种子（开发重建）
设计事实源：docs/01-architecture/r001-app-architecture.md §9.6；docs/02-modules/r001-rooms.md §6.8
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api.errors import AppError  # noqa: E402
from app.config import load_settings  # noqa: E402
from app.db.migrate import reset_schema, run_migrations, seed, table_counts  # noqa: E402
from app.db.pool import close_pool, get_conn, init_pool  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="初始化 learning_guide 数据库")
    parser.add_argument("--reset", action="store_true", help="先 DROP 全部业务表（开发重建，会丢数据）")
    parser.add_argument("--seed", action="store_true", help="写入演示种子数据（幂等）")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        settings = load_settings()
    except AppError as exc:
        print(f"[CONFIG] {exc.code}: {exc.message}")
        return 2

    init_pool(settings.database_url)
    try:
        with get_conn() as conn:
            if args.reset:
                reset_schema(conn)
                print("[reset] 已 DROP 全部业务表（含 schema_migrations）")
            applied = run_migrations(conn)
            print(f"[migrate] 本次应用版本：{', '.join(applied) if applied else '无（已是最新）'}")
            if args.seed:
                seed(conn)
                print("[seed] 演示种子数据已写入（固定 ID，重复执行不重复插入）")
            counts = table_counts(conn)
            print("[counts] 各表行数：")
            for table, count in counts.items():
                print(f"    {table:<20} {count}")
        return 0
    except Exception as exc:  # noqa: BLE001 —— 只打印异常类型与消息，绝不回显 DSN
        print(f"[ERROR] {type(exc).__name__}: {exc}")
        return 1
    finally:
        close_pool()


if __name__ == "__main__":
    raise SystemExit(main())
