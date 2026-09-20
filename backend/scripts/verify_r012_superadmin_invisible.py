"""r012 真机交叉验证：超管隐身（两个浏览器 / 两个账号）+ 大屏面板的动效降级。

为什么要这个脚本：r012 的核心口径「超管以隐身方式在场」有两层——
① 我们自己的界面/接口层（用例已覆盖）；② **LiveKit 媒体层**（`hidden=true` 才会让其它客户端
根本看不到他）。第二层只能连**真浏览器**验：本脚本起两个隔离 Chrome，各登一个账号进同一房间，
再从**成员端**（DOM）与**LiveKit 服务端 API**（参与者权限）两侧取证。

用法（先 `dev.bat` 起后端 8000 + 前端 5173）：
  python backend/scripts/verify_r012_superadmin_invisible.py
  python backend/scripts/verify_r012_superadmin_invisible.py --skip-media   # 只跑隐身交叉验证
  python backend/scripts/verify_r012_superadmin_invisible.py --room room_xxx --keep-chrome

已知抖动（2026-09-20 实测）：与其它 headless-Chrome 套件**并发连跑**时，成员端首连可能超过等待窗口 → 出现
「成员端已连上实时服务」等 3 条假失败；单独复跑 PASS 17/17。建议逐套串行跑（本脚本已把等待窗口放宽到 20 秒）。

判据：逐条打印 `[OK]/[FAIL]`，末尾 `PASS n/n`；任一步不符即非 0 退出。
依赖：`websockets`（learningguide 环境已有）+ 本机 Chrome；**不装任何新依赖**。
副作用：两个临时 Chrome 的 profile 在 `%TEMP%\lg_r012_verify\`；结束时一律 `Browser.close`（不 taskkill）；
        房间会多一条超管的 `room_visits` 记录，脚本跑完用仓储函数 `close_room_visit` 关掉；
        成员端在无麦克风的无头浏览器里**不会发布任何音频**（`--mute-audio`，tracks 实测为空）。

事实源：docs/rounds/r012-superadmin-console/review.md §1（E2/E13）、§4（降级复测）、ADR-0024。
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]
MEMBER_EMAIL, ADMIN_EMAIL, PASSWORD = "host@example.com", "admin@example.com", "demo1234"
PROFILE_ROOT = os.path.join(os.environ.get("TEMP", "."), "lg_r012_verify")

FAILURES: list[str] = []
CHECKS = 0


def check(step: str, condition: bool, detail: str) -> None:
    global CHECKS
    CHECKS += 1
    print(f"[{'OK ' if condition else 'FAIL'}] {step} — {detail}")
    if not condition:
        FAILURES.append(step)


# ---------------------------------------------------------------- CDP（零依赖最小客户端）
def http_json(port: int, path: str):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=3) as resp:
        return json.loads(resp.read().decode())


def wait_cdp(port: int, seconds: float = 25.0) -> dict:
    deadline = time.time() + seconds
    last: Exception | None = None
    while time.time() < deadline:
        try:
            return http_json(port, "/json/version")
        except Exception as exc:      # 端口刚起时会 ConnectionRefused，属正常
            last = exc
            time.sleep(0.4)
    raise RuntimeError(f"CDP 端口 {port} 没起来：{last}")


class Page:
    def __init__(self, port: int) -> None:
        self.port = port
        self._id = 0

    async def __aenter__(self) -> "Page":
        import websockets
        deadline = time.time() + 10
        target = None
        while time.time() < deadline:
            pages = [t for t in http_json(self.port, "/json/list") if t.get("type") == "page"]
            if pages:
                target = pages[0]
                break
            await asyncio.sleep(0.3)
        if target is None:
            raise RuntimeError(f"端口 {self.port} 上没有可用的页面目标")
        self._ws = await websockets.connect(target["webSocketDebuggerUrl"], max_size=40_000_000)
        for method in ("Runtime.enable", "Page.enable", "Log.enable"):
            await self.call(method)
        return self

    async def __aexit__(self, *exc) -> None:
        await self._ws.close()

    async def call(self, method: str, **params):
        self._id += 1
        mid = self._id
        await self._ws.send(json.dumps({"id": mid, "method": method, "params": params}))
        while True:
            raw = json.loads(await self._ws.recv())
            if raw.get("id") == mid:
                if "error" in raw:
                    raise RuntimeError(f"{method}: {raw['error']}")
                return raw.get("result", {})

    async def js(self, expression: str):
        out = await self.call("Runtime.evaluate", expression=expression, returnByValue=True, awaitPromise=True)
        return out.get("result", {}).get("value")

    async def goto(self, url: str, wait: float) -> None:
        await self.call("Page.navigate", url=url)
        await asyncio.sleep(wait)

    async def shot(self, path: str) -> str:
        out = await self.call("Page.captureScreenshot", format="png")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(base64.b64decode(out["data"]))
        return path


def launch_chrome(port: int, role: str) -> subprocess.Popen:
    exe = next((c for c in CHROME_CANDIDATES if os.path.exists(c)), None)
    if exe is None:
        raise RuntimeError("找不到本机 Chrome，本脚本需要它做真机取证")
    profile = os.path.join(PROFILE_ROOT, role)
    os.makedirs(profile, exist_ok=True)
    return subprocess.Popen(
        [exe, "--headless=new", f"--remote-debugging-port={port}", f"--user-data-dir={profile}",
         "--no-first-run", "--no-default-browser-check", "--disable-gpu", "--mute-audio",
         "--window-size=1440,900", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


async def login(page: Page, base: str, email: str) -> dict:
    await page.goto(f"{base}/login", wait=2.5)
    raw = await page.js(
        """(async () => {
          const r = await fetch('/api/auth/login', {method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify({email: %s, password: %s})});
          const j = await r.json();
          return JSON.stringify({status: r.status, name: j?.data?.user?.displayName, role: j?.data?.user?.role});
        })()""" % (json.dumps(email), json.dumps(PASSWORD))
    )
    return json.loads(raw)


SNAPSHOT_JS = """JSON.stringify({
  badge: (document.querySelector('.live-badge')||{}).textContent,
  tiles: document.querySelectorAll('.live-cell').length,
  tileNames: [...document.querySelectorAll('.live-tile-name')].map(e => e.textContent),
  countText: (document.body.innerText.match(/\d+\s*\/\s*\d+\s*成员/) || [''])[0],
  dock: [...document.querySelectorAll('.live-dock button, .live-superadmin-chip')].map(e => e.textContent.trim()),
  superadminChip: (document.querySelector('.live-superadmin-chip')||{}).textContent || null,
  hasMic: !!document.querySelector('.live-ctrl[title*="麦克风"]'),
  hasCam: !!document.querySelector('.live-ctrl[title*="摄像头"]'),
  hasShare: !!document.querySelector('.live-ctrl[title*="共享"]'),
  hasHand: !!document.querySelector('.live-ctrl-hand')
})"""

OPEN_MEMBERS_JS = """(async () => {
  // 抽屉开合是同一个按钮的 toggle：已经开着就别再点，否则会把它关掉（读到空串会让断言假通过）
  if (!document.querySelector('aside.live-drawer')) {
    const btn = [...document.querySelectorAll('button')].find(b => b.textContent.includes('讨论与成员'));
    if (btn) btn.click();
    await new Promise(r => setTimeout(r, 600));
  }
  const tab = [...document.querySelectorAll('.live-drawer-tab')].find(b => b.textContent.includes('成员'));
  if (tab && !tab.classList.contains('on')) {
    tab.click();
    await new Promise(r => setTimeout(r, 500));
  }
  const drawer = document.querySelector('aside.live-drawer');
  return drawer ? drawer.innerText.replace(/\s+/g, ' ').slice(0, 800) : '';
})()"""

MEASURE_JS = """JSON.stringify((() => {
  const d = document.querySelector('aside.gc-drawer');
  if (!d) return {mounted: false};
  const s = getComputedStyle(d);
  return {mounted: true, open: d.classList.contains('on'), transitionProperty: s.transitionProperty,
          transitionDuration: s.transitionDuration, transform: s.transform,
          reduced: window.matchMedia('(prefers-reduced-motion: reduce)').matches};
})())"""


def pick_room() -> str:
    """挑一间「成员是 host@example.com、超管不是成员」的进行中房间。"""
    from app.config import load_settings
    from app.db.pool import get_conn, init_pool

    settings = load_settings()
    init_pool(settings.database_url)
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT r.id FROM rooms r
            JOIN users host ON host.id = r.host_id
            WHERE r.status = 'active'
              AND host.email = %s
              AND NOT EXISTS (SELECT 1 FROM room_members m WHERE m.room_id = r.id AND m.user_id = 'usr_demo_admin')
            ORDER BY r.created_at DESC LIMIT 1
            """,
            (MEMBER_EMAIL,),
        ).fetchone()
    return row[0] if row else ""


async def livekit_participants(room_id: str) -> list[dict]:
    from livekit import api

    from app.config import load_settings

    settings = load_settings()
    if True:
        client = api.LiveKitAPI(settings.livekit_url, settings.livekit_api_key, settings.livekit_api_secret)
        try:
            resp = await client.room.list_participants(api.ListParticipantsRequest(room=room_id))
            return [
                {
                    "identity": p.identity,
                    "name": p.name,
                    "attributes": dict(p.attributes),
                    "hidden": bool(getattr(p.permission, "hidden", False)),
                    "canPublish": p.permission.can_publish,
                    "canPublishData": p.permission.can_publish_data,
                    "tracks": [str(t.type) for t in p.tracks],
                }
                for p in resp.participants
            ]
        finally:
            await client.aclose()


async def close_browser(port: int) -> None:
    """收尾：让脚本自己起的浏览器干净退出（不 taskkill）。"""
    import websockets

    info = http_json(port, "/json/version")
    async with websockets.connect(info["webSocketDebuggerUrl"]) as ws:
        await ws.send(json.dumps({"id": 1, "method": "Browser.close"}))
        try:
            await asyncio.wait_for(ws.recv(), timeout=3)
        except Exception:
            pass


async def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="r012 超管隐身真机交叉验证")
    parser.add_argument("--base-url", default="http://localhost:5173", help="前端地址（Vite 只绑 ::1，用 localhost）")
    parser.add_argument("--room", default="", help="目标房间 id（默认按库自动挑）")
    parser.add_argument("--member-port", type=int, default=9222)
    parser.add_argument("--admin-port", type=int, default=9223)
    parser.add_argument("--skip-media", action="store_true", help="只跑隐身交叉验证，跳过 reduced-motion")
    parser.add_argument("--keep-chrome", action="store_true", help="跑完不关浏览器（排障用）")
    args = parser.parse_args(argv)
    base, room_id = args.base_url.rstrip("/"), args.room or pick_room()
    shots = os.path.join(os.environ.get("TEMP", "."), "lg_r012")
    chrome: list[subprocess.Popen] = []

    if not room_id:
        print("[FAIL] 没找到可用的进行中房间（需要 host@example.com 是房主且超管不是成员）；先 db_init --seed")
        return 2
    print(f"目标房间：{room_id}；前端：{base}")

    try:
        chrome.append(launch_chrome(args.member_port, "member"))
        chrome.append(launch_chrome(args.admin_port, "admin"))
        for port in (args.member_port, args.admin_port):
            info = wait_cdp(port)
            print(f"  [i] CDP {port} 就绪：{info['Browser']} / 协议 {info['Protocol-Version']}")

        # ① 成员端先单独进房，取基线
        async with Page(args.member_port) as member:
            who = await login(member, base, MEMBER_EMAIL)
            check("成员端登录", who.get("status") == 200, f"→ {who}")
            # 等窗口放宽到 20 秒：多套 headless Chrome 并发连跑时首次连 LiveKit 明显变慢（8 秒不够 → 会误报「成员端未连上」）
            await member.goto(f"{base}/rooms/{room_id}/live", wait=20)
            before = json.loads(await member.js(SNAPSHOT_JS))
            drawer_before = await member.js(OPEN_MEMBERS_JS)
            check("成员端已连上实时服务", before["badge"] == "已连接", f"→ 徽标 {before['badge']!r}")
            check("基线：成员端舞台只有自己", before["tiles"] == 1 and len(before["tileNames"]) == 1,
                  f"→ {before['tiles']} 格 {before['tileNames']}")
            check("基线：成员抽屉读到了内容且没有管理员",
                  bool(drawer_before) and "平台管理员" not in drawer_before,
                  f"→ 长度 {len(drawer_before)}，片段 {drawer_before[:80]!r}")
            await member.shot(os.path.join(shots, "v-member-before.png"))

            # ② 超管端进同一间房
            async with Page(args.admin_port) as admin:
                who_admin = await login(admin, base, ADMIN_EMAIL)
                check("超管端登录", who_admin.get("role") == "superadmin", f"→ {who_admin}")
                await admin.goto(f"{base}/rooms/{room_id}/live", wait=12)
                adm = json.loads(await admin.js(SNAPSHOT_JS))
                check("超管端：隐身标识与控制坞", adm["superadminChip"] == "管理视角 · 隐身",
                      f"→ chip={adm['superadminChip']!r} dock={adm['dock']}")
                check("超管端：没有麦克风/摄像头/共享/举手控件",
                      not (adm["hasMic"] or adm["hasCam"] or adm["hasShare"] or adm["hasHand"]),
                      f"→ mic={adm['hasMic']} cam={adm['hasCam']} share={adm['hasShare']} hand={adm['hasHand']}")
                await admin.shot(os.path.join(shots, "v-admin-in-room.png"))

                # ③ 成员端复看：超管在场但看不见
                after = json.loads(await member.js(SNAPSHOT_JS))
                drawer_after = await member.js(OPEN_MEMBERS_JS)
                check("成员端舞台格数不变（超管不占格）", after["tiles"] == before["tiles"],
                      f"→ 进房前 {before['tiles']} 格，进房后 {after['tiles']} 格 {after['tileNames']}")
                check("成员端在册人数不变（不计入人数）", after["countText"] == before["countText"] and bool(after["countText"]),
                      f"→ 前 {before['countText']!r} / 后 {after['countText']!r}")
                check("成员端成员抽屉仍看不到管理员",
                      bool(drawer_after) and "平台管理员" not in drawer_after,
                      f"→ 长度 {len(drawer_after)}，片段 {drawer_after[:80]!r}")
                await member.shot(os.path.join(shots, "v-member-after.png"))

                # ④ LiveKit 服务端视角（媒体层的最终裁判）
                parts = await livekit_participants(room_id)
                by_id = {p["identity"]: p for p in parts}
                member_p = next((p for p in parts if not p["hidden"]), None)
                admin_p = next((p for p in parts if p["attributes"].get("lg-role") == "superadmin"), None)
                check("LiveKit：成员是普通参与者（可发布）", bool(member_p and member_p["canPublish"]),
                      f"→ {member_p}")
                check("LiveKit：超管 hidden=true 且禁止发布",
                      bool(admin_p and admin_p["hidden"] and not admin_p["canPublish"] and not admin_p["canPublishData"]),
                      f"→ {admin_p}")
                check("LiveKit：超管没有发布任何轨道", bool(admin_p and not admin_p["tracks"]),
                      f"→ tracks={admin_p['tracks'] if admin_p else None}")

        # ⑤ reduced-motion 强制模拟（CDP Emulation.setEmulatedMedia）
        if not args.skip_media:
            async with Page(args.member_port) as page:
                await page.goto(f"{base}/", wait=3)
                await page.js("""(async () => {
                  const b = [...document.querySelectorAll('button')].find(x => x.textContent.trim() === '大屏');
                  if (b) b.click();
                  await new Promise(r => setTimeout(r, 500));
                  return true;
                })()""")
                normal = json.loads(await page.js(MEASURE_JS))
                await page.call("Emulation.setEmulatedMedia", media="screen",
                                features=[{"name": "prefers-reduced-motion", "value": "reduce"}])
                await page.js("""(async () => {
                  const d = document.querySelector('aside.gc-drawer button');
                  if (d) d.click();                       // 收起（reduce 下应瞬时到位）
                  await new Promise(r => setTimeout(r, 200));
                  return true;
                })()""")
                reduced_closed = json.loads(await page.js(MEASURE_JS))
                await page.js("""(async () => {
                  const b = [...document.querySelectorAll('button')].find(x => x.textContent.trim() === '大屏');
                  if (b) b.click();                       // 再打开
                  await new Promise(r => setTimeout(r, 150));
                  return true;
                })()""")
                reduced_open = json.loads(await page.js(MEASURE_JS))
                await page.call("Emulation.setEmulatedMedia", media="screen", features=[])
                check("常规：面板过渡 0.24s（= --t-base）",
                      normal.get("transitionDuration", "").startswith("0.24s"), f"→ {normal}")
                check("reduce：过渡被关掉（transition-property none）",
                      reduced_closed.get("transitionProperty") == "none" and reduced_closed.get("reduced") is True,
                      f"→ {reduced_closed}")
                check("reduce：收起态在 200ms 内已关（无位移过渡）",
                      reduced_closed.get("open") is False and reduced_closed.get("transform") == "matrix(1, 0, 0, 1, 376, 0)",
                      f"→ {reduced_closed}")
                check("reduce：点击后 150ms 即到位（无位移过渡）",
                      reduced_open.get("open") is True and reduced_open.get("transform") == "matrix(1, 0, 0, 1, 0, 0)",
                      f"→ {reduced_open}")
                await page.shot(os.path.join(shots, "v-reduced-motion.png"))

        # ⑥ 收尾：关掉脚本自己造的那条超管访问记录
        try:
            from datetime import datetime, timezone

            from app.db.pool import get_conn
            from app.repositories import rooms as rooms_repo

            with get_conn() as conn:
                closed = rooms_repo.close_room_visit(conn, room_id, "usr_demo_admin", datetime.now(timezone.utc))
            print(f"  [i] 收尾：关闭超管 room_visits 记录 {closed} 行")
        except Exception as exc:  # noqa: BLE001 - 收尾失败不该掩盖验证结论
            print(f"  [!] 收尾关闭 room_visits 失败（不影响结论）：{type(exc).__name__}: {exc}")
        print(f"  [i] 截图目录：{shots}")
    finally:
        if not args.keep_chrome:
            for port in (args.member_port, args.admin_port):
                try:
                    await close_browser(port)
                    print(f"  [i] Browser.close 端口 {port}")
                except Exception:
                    pass

    total = CHECKS
    if FAILURES:
        print(f"\nFAIL {len(FAILURES)}/{total} — 失败项：{', '.join(FAILURES)}")
        return 1
    print(f"\nPASS {total}/{total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main(sys.argv[1:])))
