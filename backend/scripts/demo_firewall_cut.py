"""演示道具（网络层真断）：用**临时防火墙规则**把本机到 LiveKit 的出网掐掉 N 秒，然后自动删规则。

为什么比「冻进程」更好：断的过程中**两个窗口都在正常渲染**，Chrome 网络栈如实报失败 → 被断端和另一端
**在断的过程中就能看到「正在重连…」**（冻进程那条只能看到画面卡住）。

代价与风险（照实写）：
- 这是**整机**级别的阻断：本机所有经 LiveKit 的连接都会断（演示时两个窗口都会显示「正在重连…」，恢复后都自己回来）。
- 需要**管理员**权限（netsh advfirewall）。
- 脚本 `try/finally` 保证删规则；**万一进程被强杀**，规则会残留 → 用 `--remove` 或
  `netsh advfirewall firewall delete rule name="lg-demo-cut"` 手动删掉。脚本每次启动也会先清同名旧规则。
- 只拦 LiveKit 的 IP（从 .env 的 LIVEKIT_URL 解析），不动别的网站。

用法：
    python backend/scripts/demo_firewall_cut.py --status        # 看规则与解析到的 IP（不动手）
    python backend/scripts/demo_firewall_cut.py --dry-run       # 只打印将要执行的两条 netsh
    python backend/scripts/demo_firewall_cut.py --seconds 12    # 真断 12 秒后自动恢复
    python backend/scripts/demo_firewall_cut.py --remove        # 手动清规则（兜底）
"""
from __future__ import annotations

import argparse
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

RULE_NAME = "lg-demo-cut"
REPO_ROOT = Path(__file__).resolve().parents[2]

CHECKLIST = """台上怎么说/看什么（2026-09-20 实测口径）：
  · 断的**过程中**（不是恢复后）：两个窗口都在正常渲染，被断端状态条几秒内变「正在重连…」（控制坞变灰）
  · 地址栏一直没跳走、页面没白屏
  · 恢复后几秒内自己回到「已连接」，**不用点任何按钮**；举手/焦点保持（若断前是举手者）
  · 另一端：成员列表里那位变「不在房间」→ 恢复后回到「在房间里」"""


def load_livekit_host() -> str:
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return ""
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip().startswith("LIVEKIT_URL="):
            url = line.split("=", 1)[1].strip()
            match = re.match(r"wss?://([^/]+)", url)
            return match.group(1) if match else ""
    return ""


def resolve_ips(host: str) -> list[str]:
    infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    return sorted({info[4][0] for info in infos})


def is_admin() -> bool:
    """直接问 Windows（比拉 PowerShell 子进程可靠：后者容易受引号/编码影响而误判）。"""
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:  # noqa: BLE001
        return False


def _netsh(*args: str) -> subprocess.CompletedProcess:
    """netsh 在中文 Windows 控制台是 GBK 输出，按 gbk 解码（按 utf-8 会乱码）。"""
    return subprocess.run(["netsh", "advfirewall", "firewall", *args],
                          capture_output=True, text=True, encoding="gbk", errors="replace", timeout=60)


def rule_exists() -> bool:
    out = _netsh("show", "rule", f"name={RULE_NAME}")
    return out.returncode == 0 and RULE_NAME in (out.stdout or "")


def remove_rule() -> bool:
    if not rule_exists():
        return True
    out = _netsh("delete", "rule", f"name={RULE_NAME}")
    ok = out.returncode == 0
    print(f"  {'✔' if ok else '✘'} 删规则 {RULE_NAME}：{(out.stdout or out.stderr or '').strip()[:120]}")
    return ok


def add_rule(ips: list[str]) -> bool:
    out = _netsh("add", "rule", f"name={RULE_NAME}", "dir=out", "action=block", "protocol=any",
                 "profile=any", f"remoteip={','.join(ips)}")
    ok = out.returncode == 0
    print(f"  {'✔' if ok else '✘'} 加规则 {RULE_NAME}（拦 {len(ips)} 个 IP）：{(out.stdout or out.stderr or '').strip()[:120]}")
    return ok


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="演示道具：临时防火墙掐断 LiveKit 出网 N 秒")
    ap.add_argument("--host", default="", help="默认从 .env 的 LIVEKIT_URL 取域名")
    ap.add_argument("--seconds", type=float, default=12.0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--remove", action="store_true", help="手动清规则（兜底）")
    args = ap.parse_args(argv)

    host = args.host or load_livekit_host()
    if not host:
        print("[!] 没拿到 LiveKit 域名（.env 里没 LIVEKIT_URL？可用 --host 指定）")
        return 2
    ips = resolve_ips(host)
    masked = re.sub(r"^[^.]+", "<sub>", host)
    print(f"目标：{masked} → {len(ips)} 个 IP：{', '.join(ips)}")
    print(f"当前状态：管理员={is_admin()}｜规则 {RULE_NAME} 存在={rule_exists()}")

    if args.status:
        return 0
    if args.remove:
        remove_rule()
        return 0
    if args.dry_run:
        print("将执行：")
        print(f"  netsh advfirewall firewall delete rule name={RULE_NAME}")
        print(f"  netsh advfirewall firewall add rule name={RULE_NAME} dir=out action=block "
              f"protocol=any profile=any remoteip={','.join(ips)}")
        print(f"  （等 {args.seconds:.0f} 秒）")
        print(f"  netsh advfirewall firewall delete rule name={RULE_NAME}")
        return 0

    if not is_admin():
        print("[!] 需要管理员权限。请右键以管理员身份运行 demo-firewall-cut.bat（或提权后重跑）。")
        return 3

    print(f"\n▶ 掐断 LiveKit 出网 {args.seconds:.0f} 秒 —— 现在让台下看两个窗口的状态条")
    remove_rule()          # 先清同名旧规则，避免残留叠加
    if not add_rule(ips):
        print("[!] 加规则失败，未做任何阻断")
        return 4
    try:
        remaining = args.seconds
        while remaining > 0:
            step = min(1.0, remaining)
            time.sleep(step)
            remaining -= step
            if remaining > 0:
                print(f"  … 还剩 {remaining:.0f} 秒", flush=True)
    finally:
        print("\n◀ 恢复出网（删规则）")
        if not remove_rule():
            print(f"[!] 删规则失败！请手动执行：netsh advfirewall firewall delete rule name={RULE_NAME}")
            return 5
    print()
    print(CHECKLIST)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
