"""演示道具：把**某个固定演示账号的那个浏览器窗口**真断一下，N 秒后恢复（进程级真中断）。

⚠️ 实测边界（2026-09-20 本机三次运行，照实写，别在台上当保证）：
- **有效**：断的是那个窗口的网络服务子进程，恢复后 SDK 会自己重连 —— 一次 12 秒冻结实测：恢复后约
  1.5 秒出现「正在重连…」、约 4.5 秒回到「已连接」，**举手状态保持**、地址栏没跳走。
- **不稳**：另一次 10 秒冻结后停在「已断开」，**没有自动回来**（冻结期间的 LiveKit 会话状态不定）
  → 建议 `--seconds 12`，台上按「兜底」讲：真不回来就「房间列表 → 回到讨论」重进（三秒的事）。
- **观感限制**：断的过程中该窗口**画面停在「已连接」**（Chrome 自己的网络栈也被冻住，不再报超时），
  台下的可见证据是**另一端的成员列表**（该成员变「不在房间」）。要让「正在重连…」在断的过程中就出现在
  被断的那一端，需要网络层真阻断（临时防火墙规则 / 物理断网），那要动系统设置 —— 见 r013 需求单 §10.5。

原始用途：把**某个固定演示账号的那个浏览器窗口**真断一下，N 秒后恢复。

用途：答辩/录屏现场演「断线重连」——台下要看到那端状态条从「已连接」变「正在重连…」，几秒后自己回到
「已连接」，且设备与举手/焦点保持。**只动演示账号自己的窗口**（按浏览器 profile 目录精确定位），
不动其它窗口、不改系统设置、不碰网络、不需要管理员权限。

原理：对目标窗口的**全部** chrome.exe 进程（浏览器主进程 + 渲染 + 网络服务）调 `NtSuspendProcess`
（等价于把那个窗口冻住）→ 该端停止收发（LiveKit 侧心跳超时，从它的视角就是断线）→ N 秒后
`NtResumeProcess` 恢复 → SDK 自己重连。**这是真中断**（客户端真的停止通信），不是前端假装。

用法（配 `demo-window.bat` 使用）：
    demo-window.bat part                # ① 先开演示账号窗口（固定 profile，登录一次记住）
    demo-disconnect.bat                 # ② 演示时点一下：默认断 part 10 秒
    demo-disconnect.bat 12 host         #    或指定秒数与角色（host / mod / part / admin）

直接跑 python：
    python backend/scripts/demo_disconnect.py --list                 # 只列出目标进程（dry-run）
    python backend/scripts/demo_disconnect.py --role part --seconds 10
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROLES = ("host", "mod", "part", "admin")
PROFILE_ROOT = os.path.join(os.environ.get("TEMP", "."), "lg_demo")
PROCESS_SUSPEND_RESUME = 0x0800

CHECKLIST = """该看什么（2026-09-20 实测口径，别超出实际观感讲）：
  · 断的过程中：**被断窗口画面不动**（停在断前那一帧，仍写「已连接」）→ 让台下看**另一端**：
    成员列表里那位变「不在房间」（实测约在断后 2~3 秒生效）
  · 恢复后（约 1~2 秒）：被断窗口出现「正在重连…」（控制坞变灰）
  · 再约 2~4 秒：自己回到「已连接」，地址栏没跳走、页面没白屏，**举手/焦点保持**（若断前是举手者）
  · 兜底：若 8 秒后仍停在「已断开」→ 点「房间列表 → 回到讨论」重进（实测出现过一次，别赌）"""


def profile_dir(role: str) -> str:
    return os.path.join(PROFILE_ROOT, role)


NETWORK_SUBTYPE = "network.mojom.NetworkService"
"""Chrome 把网络 I/O 放在独立子进程里；只冻它 = 该窗口收不到网但**页面照常渲染**（台下能看到「正在重连…」）。"""


def list_target_processes(role: str, target: str = "network") -> list[dict]:
    """按 profile 目录匹配该演示窗口的全部 chrome.exe 进程（用命令行精确匹配，不按名字乱杀）。"""
    target = profile_dir(role)
    script = (
        "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
        "Where-Object { $_.CommandLine -and $_.CommandLine.Contains('%s') } | "
        "Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Compress"
    ) % target.replace("'", "''")
    out = subprocess.run(["powershell", "-NoProfile", "-Command", script],
                         capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    text = (out.stdout or "").strip()
    if not text:
        return []
    data = json.loads(text)
    if isinstance(data, dict):
        data = [data]
    items = [{"pid": int(item["ProcessId"]), "parent": int(item.get("ParentProcessId") or 0),
              "cmd": item.get("CommandLine") or ""} for item in data]
    if target == "network":
        net = [item for item in items if NETWORK_SUBTYPE in item["cmd"]]
        return net or items     # 找不到网络服务子进程就退回整窗（并在调用处提示）
    return items


def _open(pid: int):
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    handle = kernel32.OpenProcess(PROCESS_SUSPEND_RESUME, False, pid)
    if not handle:
        raise OSError(f"OpenProcess({pid}) 失败：{ctypes.get_last_error()}")
    return handle


def suspend(pids: list[int]) -> list[int]:
    ntdll = ctypes.WinDLL("ntdll")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    done: list[int] = []
    for pid in pids:
        try:
            handle = _open(pid)
            status = ntdll.NtSuspendProcess(handle)
            kernel32.CloseHandle(handle)
            if status == 0:
                done.append(pid)
            else:
                print(f"  [!] 挂起 {pid} 返回状态 {status}")
        except OSError as exc:
            print(f"  [!] 挂起 {pid} 失败：{exc}")
    return done


def resume(pids: list[int]) -> list[int]:
    ntdll = ctypes.WinDLL("ntdll")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    done: list[int] = []
    for pid in pids:
        try:
            handle = _open(pid)
            status = ntdll.NtResumeProcess(handle)
            kernel32.CloseHandle(handle)
            if status == 0:
                done.append(pid)
            else:
                print(f"  [!] 恢复 {pid} 返回状态 {status}")
        except OSError as exc:
            print(f"  [!] 恢复 {pid} 失败：{exc}")
    return done


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="演示道具：把固定演示账号的窗口真断 N 秒再恢复")
    ap.add_argument("--role", default="part", choices=ROLES, help="演示账号角色（对应 demo-window.bat 开的窗口）")
    ap.add_argument("--seconds", type=float, default=10.0, help="断多久（秒）；建议 ≥10，太短 LiveKit 侧不会判超时")
    ap.add_argument("--list", action="store_true", help="只列出目标进程（dry-run，不动它）")
    ap.add_argument("--keep-frozen", action="store_true", help="恢复前停下（危险：窗口会一直冻着，仅排障用）")
    ap.add_argument("--target", default="network", choices=("network", "tree"),
                    help="network=只冻网络服务子进程（页面仍渲染，台下能看到「正在重连…」）；tree=整窗冻住（台下看到窗口卡住）")
    args = ap.parse_args(argv)

    targets = list_target_processes(args.role, args.target)
    print(f"目标：角色 {args.role} → profile {profile_dir(args.role)}（target={args.target}）")
    if not targets:
        print("  [!] 没找到该角色的浏览器窗口。先跑 demo-window.bat " + args.role + " 打开它（窗口开着才能断）。")
        return 2
    if args.target == "network" and targets and NETWORK_SUBTYPE not in targets[0]["cmd"]:
        print("  [!] 没找到该窗口的网络服务子进程 → 退回整窗冻结（台下会看到窗口卡住，不是「正在重连…」）")
    print(f"  命中 {len(targets)} 个进程：{', '.join(str(t['pid']) for t in targets)}")
    if args.list:
        print("（--list：只列不动）")
        return 0

    print(f"\n▶ 断线 {args.seconds:.0f} 秒 —— 现在可以让台下看状态条了")
    frozen = suspend([t["pid"] for t in targets])
    print(f"  已挂起 {len(frozen)} 个进程；开始倒计时")
    try:
        remaining = args.seconds
        while remaining > 0:
            step = min(1.0, remaining)
            time.sleep(step)
            remaining -= step
            if remaining > 0:
                print(f"  … 还剩 {remaining:.0f} 秒", flush=True)
        if args.keep_frozen:
            print("  [!] --keep-frozen：保持冻结，恢复请手动再跑一次不带该参数的命令")
            return 0
    finally:
        back = resume([t["pid"] for t in targets])
        print(f"\n◀ 已恢复 {len(back)} 个进程（它会自己重连，不用点按钮）")
    print()
    print(CHECKLIST)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
