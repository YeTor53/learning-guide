"""把某个账号设为 / 取消超管（r012）。

用法（仓库根目录，conda 环境 learningguide）：
  python backend/scripts/grant_superadmin.py --email someone@example.com            # 提权
  python backend/scripts/grant_superadmin.py --email someone@example.com --revoke   # 降权

设计事实源：docs/rounds/r012-superadmin-console/design.md §2.5。
- 幂等：已是目标角色时照样执行（影响 1 行），输出改前 → 改后；
- 找不到邮箱 → 退出码 2 并提示先注册（零副作用）；
- 绝不回显口令材料，只打印邮箱 / 角色 / 行数 / 用户 id。
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
from app.db.pool import close_pool, get_conn, init_pool  # noqa: E402
from app.repositories import users as users_repo  # noqa: E402
from app.schemas.common import normalize_email  # noqa: E402
from app.services.roles import SUPERADMIN, USER, VALID_ROLES  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="设置 / 取消某个账号的超管角色")
    parser.add_argument("--email", required=True, help="目标账号邮箱（大小写不敏感）")
    parser.add_argument("--revoke", action="store_true", help="取消超管（改回普通用户）")
    parser.add_argument("--role", choices=VALID_ROLES, help="直接指定角色（默认按 --revoke 推导）")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    email = normalize_email(args.email)
    target = args.role or (USER if args.revoke else SUPERADMIN)
    try:
        settings = load_settings()
    except AppError as exc:
        print(f"[CONFIG] {exc.code}: {exc.message}")
        return 2

    init_pool(settings.database_url)
    try:
        with get_conn() as conn:
            row = users_repo.get_user_by_email(conn, email)
            if row is None:
                print(f"[ERROR] 找不到账号：{email}（先注册该邮箱，或用 seed 里的 admin@example.com）")
                return 2
            with conn.transaction():
                changed = users_repo.set_user_role(conn, row.id, target)
            print(f"[role] {email}：{row.role} → {target}（影响 {changed} 行；id={row.id}）")
        return 0
    except Exception as exc:  # noqa: BLE001 —— 只打印类型与消息，不回显 DSN
        print(f"[ERROR] {type(exc).__name__}: {exc}")
        return 1
    finally:
        close_pool()


if __name__ == "__main__":
    raise SystemExit(main())
