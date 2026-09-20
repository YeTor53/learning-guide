"""演示库清理：只清**测试垃圾**，保住 seed 与你的演示房 / 演示账号。

为什么需要它：`smoke.py`、`pytest`、各轮真机自检脚本每跑一次都会往库里写测试房与测试账号
（本轮实测一次门禁就留下 78 间 + 一批账号）。而 `db_init.py --reset --seed` 会把库**整**恢复成 seed，
连你自己手工建的演示房（如「德意志的兴衰——最后的帝国」）一起删掉 —— 所以这里按规则**选择性**清。

保留规则（两条同时满足才保留一间房）：
  1. 房主是**演示账号**（host@ / mod@ / part@ / admin@ example.com）
  2. 标题不含测试关键词（自检 / 冒烟 / 调试 / 强停 / 时序 / 回归房 / 探查房 / 截图房 / 收官 / PROBE /
     探针 / 铺满 / 动效 / 闭环 / 给焦点 / 焦点前端 / 声波 / E2E / dbg / 以及历史轮次房名 r0xx / cp7 等）
账号：只留上面 4 个演示账号，其余（`*@example.com` 的脚本账号）删除。
另外清空：`room_hand_raises`、`room_visits`（测试残留的举手/访问记录）、以及 body 命中测试关键词的
`global_messages`（大屏测试消息）。**审计表 `admin_audit` 不动**（它是演示里要看的留痕）。

用法：
    python backend/scripts/clean_demo_junk.py              # 干跑：只打印将要删什么（默认）
    python backend/scripts/clean_demo_junk.py --yes        # 真删（一个事务）
    python backend/scripts/clean_demo_junk.py --keep-users # 只清房，不动账号
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import load_settings          # noqa: E402
from app.db.pool import get_conn, init_pool   # noqa: E402

DEMO_EMAILS = "('host@example.com','mod@example.com','part@example.com','admin@example.com')"
ROOM_TEST_PATTERN = (r"自检|冒烟|调试|强停|时序|回归房|探查房|截图房|收官|PROBE|探针|铺满|动效|闭环|给焦点|"
                     r"焦点前端|声波|E2E|dbg|^p[2-5] |^r[0-9]|^cp[0-9]|取证|阶梯|测试房间|（临时）")
MSG_TEST_PATTERN = r"自检|大屏跨端|探针|冒烟|调试|SSE 修复验证|游客不该能发|来自另一个客户端|真机取证"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="演示库清理（选择性，保 seed 与演示房）")
    ap.add_argument("--yes", action="store_true", help="真删（默认只干跑）")
    ap.add_argument("--keep-users", action="store_true", help="只清房，不动账号")
    args = ap.parse_args(argv)

    init_pool(load_settings().database_url)
    with get_conn() as conn:
        rooms_keep = conn.execute(
            f"""SELECT coalesce(title,'(无标题)'), status FROM rooms r JOIN users u ON u.id=r.host_id
                WHERE u.email IN {DEMO_EMAILS} AND (title IS NULL OR title !~ %s)
                ORDER BY r.created_at""", (ROOM_TEST_PATTERN,)).fetchall()
        rooms_drop = conn.execute(
            f"""SELECT count(*) FROM rooms r JOIN users u ON u.id=r.host_id
                WHERE NOT (u.email IN {DEMO_EMAILS} AND (title IS NULL OR title !~ %s))""",
            (ROOM_TEST_PATTERN,)).fetchone()[0]
        users_drop = conn.execute(
            f"SELECT count(*) FROM users WHERE email NOT IN {DEMO_EMAILS}").fetchone()[0]
        msg_drop = conn.execute("SELECT count(*) FROM global_messages WHERE body ~ %s",
                                (MSG_TEST_PATTERN,)).fetchone()[0]

        print(f"将保留 {len(rooms_keep)} 间房：")
        for title, status in rooms_keep:
            print(f"  {status:<7} {title}")
        print(f"将删除：房 {rooms_drop} 间｜账号 {users_drop} 个｜大屏测试消息 {msg_drop} 条"
              f"（另清空全部举手 {conn.execute('SELECT count(*) FROM room_hand_raises').fetchone()[0]} 行、"
              f"访问记录 {conn.execute('SELECT count(*) FROM room_visits').fetchone()[0]} 行）")
        if not args.yes:
            print("\n（干跑，未改库。真删加 --yes）")
            return 0

        conn.execute(f"""DELETE FROM rooms r USING users u WHERE u.id=r.host_id
                         AND NOT (u.email IN {DEMO_EMAILS} AND (r.title IS NULL OR r.title !~ %s))""",
                     (ROOM_TEST_PATTERN,))
        if not args.keep_users:
            conn.execute(f"DELETE FROM users WHERE email NOT IN {DEMO_EMAILS}")
        conn.execute("DELETE FROM room_hand_raises")
        conn.execute("DELETE FROM room_visits")
        conn.execute("DELETE FROM global_messages WHERE body ~ %s", (MSG_TEST_PATTERN,))

        left = {t: conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in
                ("rooms", "users", "room_members", "chat_messages", "global_messages", "admin_audit")}
        print("\n✔ 已清理。现存计数：" + " / ".join(f"{k} {v}" for k, v in left.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
