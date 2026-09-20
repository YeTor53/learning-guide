"""演示台本 UI 自检（r012 收尾）：按角色把真实界面上的**文案与控件**抓回来，跟台本逐条对。

为什么需要它：台本写的是「点到哪个按钮」，界面一改就容易漂。门禁（pytest / smoke / tsc / build）
测的是接口与构建，测不到「这个按钮还在不在、文案还是不是这一句」。本脚本用真 Chrome + CDP
把四个角色（未登录 / 房主 / 参与者 / 超管）走一遍，逐条断言台本点名的控件与文案。

用法（先 `dev.bat` 起后端 8000 + 前端 5173）：
  python frontend/scripts/verify-runbook-ui.py
  python frontend/scripts/verify-runbook-ui.py --keep-chrome     # 排障：跑完留浏览器
  python frontend/scripts/verify-runbook-ui.py --skip-behaviour  # 只核对文案，不建房

判据：逐条 `[OK]/[FAIL]`，末尾 `PASS n/n`；任一条不符非 0 退出。
依赖：`websockets`（learningguide 环境已有）+ 本机 Chrome；零新依赖。
副作用：两个临时 Chrome（profile 在 `%TEMP%\lg_runbook\`）；结束时 `Browser.close`；
        行为段会**新建一个临时房**（标题带 `台本自检` 前缀，跑完结束它，不删）；
        台本里「共享屏幕 / 录音录屏 / 真实语音转写」需要人工或额外进程，见脚本末尾的未覆盖清单。

事实源：`docs/00-project/demo-runbook.md`（台本）、`docs/rounds/r012-superadmin-console/review.md`。
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

CHROME = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
          r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"]
HOST_EMAIL, PART_EMAIL, ADMIN_EMAIL, PASSWORD = "host@example.com", "part@example.com", "admin@example.com", "demo1234"
PROFILE_ROOT = os.path.join(os.environ.get("TEMP", "."), "lg_runbook")

FAILURES: list[str] = []
CHECKS = 0


def check(step: str, ok: bool, detail: str) -> None:
    global CHECKS
    CHECKS += 1
    print(f"[{'OK ' if ok else 'FAIL'}] {step} — {detail}")
    if not ok:
        FAILURES.append(step)


def http_json(port: int, path: str):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=3) as resp:
        return json.loads(resp.read().decode())


def wait_cdp(port: int, seconds: float = 25.0):
    deadline, last = time.time() + seconds, None
    while time.time() < deadline:
        try:
            return http_json(port, "/json/version")
        except Exception as exc:
            last = exc
            time.sleep(0.4)
    raise RuntimeError(f"CDP {port} 没起来：{last}")


class Page:
    def __init__(self, port: int) -> None:
        self.port = port
        self._id = 0

    async def __aenter__(self) -> "Page":
        import websockets
        deadline, target = time.time() + 10, None
        while time.time() < deadline:
            pages = [t for t in http_json(self.port, "/json/list") if t.get("type") == "page"]
            if pages:
                target = pages[0]
                break
            await asyncio.sleep(0.3)
        if target is None:
            raise RuntimeError(f"端口 {self.port} 上没有页面目标")
        self._ws = await websockets.connect(target["webSocketDebuggerUrl"], max_size=40_000_000)
        for m in ("Runtime.enable", "Page.enable", "Log.enable"):
            await self.call(m)
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

    async def goto(self, url: str, wait: float = 3.0) -> None:
        await self.call("Page.navigate", url=url)
        await asyncio.sleep(wait)

    async def shot(self, path: str) -> str:
        out = await self.call("Page.captureScreenshot", format="png")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(base64.b64decode(out["data"]))
        return path


# ---- 页面探针：一次性把「可见文案清单」抓回来（按钮 / 链接 / 标签 / 占位符 / 标题 / 表格头）----
PROBE = """JSON.stringify({
  title: document.title,
  headings: [...document.querySelectorAll('h1,h2,h3')].map(e => e.innerText.trim()),
  buttons: [...document.querySelectorAll('button')].map(e => e.innerText.trim() || e.getAttribute('aria-label') || e.getAttribute('title') || ''),
  // 侧栏折叠时标签不渲染（只剩图标），此时 title 属性是唯一可核对的文案
  links: [...document.querySelectorAll('a')].map(e => e.innerText.trim() || e.getAttribute('title') || ''),
  linkTitles: [...document.querySelectorAll('a')].map(e => e.getAttribute('title') || ''),
  placeholders: [...document.querySelectorAll('input,textarea')].map(e => e.getAttribute('placeholder') || ''),
  tableHeads: [...document.querySelectorAll('th')].map(e => e.innerText.trim()),
  bodyText: document.body.innerText.replace(/\s+/g, ' ')
})"""


async def probe(page: Page) -> dict:
    return json.loads(await page.js(PROBE))


def has(probe_data: dict, text: str) -> bool:
    """文案存在性：先看结构化字段，再兜底全文（动态数值只在全文里）。"""
    blob = " | ".join(probe_data.get("buttons", []) + probe_data.get("links", [])
                      + probe_data.get("linkTitles", []) + probe_data.get("headings", [])
                      + probe_data.get("placeholders", []) + probe_data.get("tableHeads", []))
    return text in blob or text in probe_data.get("bodyText", "")


def has_re(probe_data: dict, pattern: str) -> bool:
    return re.search(pattern, probe_data.get("bodyText", "")) is not None


TOGGLE_JS = """(async () => {
  // 面板开合是同一个按钮的 toggle：已经开着就别再点（否则会把它关掉，读到空让断言假通过）
  const want = %s;
  const box = document.querySelector(%s);
  const isOpen = box ? box.classList.contains('on') : false;
  if (isOpen === want) return isOpen;
  const btn = [...document.querySelectorAll('button')].find(x => (x.textContent || '').trim() === %s);
  if (btn) btn.click();
  await new Promise(r => setTimeout(r, 700));
  const after = document.querySelector(%s);
  return after ? after.classList.contains('on') : false;
})()"""


async def set_drawer(page: Page, want_open: bool) -> bool:
    """幂等地把右侧大屏面板切到想要的状态，返回切换后的真实状态。"""
    return bool(await page.js(TOGGLE_JS % (json.dumps(want_open), json.dumps("aside.gc-drawer"),
                                            json.dumps("大屏"), json.dumps("aside.gc-drawer"))))


async def set_panel_tab(page: Page, label: str) -> None:
    """抽屉分区（讨论/成员/邀请）与后台分区（房间/用户/…）共用 .live-drawer-tab：已选中就不点。"""
    await page.js("""(async () => {
      const tab = [...document.querySelectorAll('.live-drawer-tab')].find(x => x.textContent.includes(%s));
      if (tab && !tab.classList.contains('on')) { tab.click(); await new Promise(r => setTimeout(r, 500)); }
      return true;
    })()""" % json.dumps(label))


async def wait_until(page: Page, expression: str, timeout: float = 20.0, interval: float = 0.5) -> bool:
    """轮询直到页面里的表达式为真（首次连 LiveKit 实测最慢 24 秒、后台表格要等接口返回）。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if await page.js(expression):
                return True
        except Exception:
            pass
        await asyncio.sleep(interval)
    return False


async def probe_when(page: Page, expression: str, timeout: float = 20.0) -> tuple[dict, bool]:
    ok = await wait_until(page, expression, timeout)
    return await probe(page), ok


async def login(page: Page, base: str, email: str) -> dict:
    await page.goto(f"{base}/login", 2.2)
    raw = await page.js("""(async () => {
      const r = await fetch('/api/auth/login', {method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({email: %s, password: %s})});
      const j = await r.json();
      return JSON.stringify({status: r.status, role: j?.data?.user?.role});
    })()""" % (json.dumps(email), json.dumps(PASSWORD)))
    return json.loads(raw)


def launch(port: int, role: str) -> subprocess.Popen:
    exe = next((c for c in CHROME if os.path.exists(c)), None)
    if not exe:
        raise RuntimeError("找不到本机 Chrome")
    profile = os.path.join(PROFILE_ROOT, role)
    os.makedirs(profile, exist_ok=True)
    return subprocess.Popen([exe, "--headless=new", f"--remote-debugging-port={port}", f"--user-data-dir={profile}",
                             "--no-first-run", "--no-default-browser-check", "--disable-gpu", "--mute-audio",
                             "--window-size=1440,900", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


async def close_browser(port: int) -> None:
    import websockets
    info = http_json(port, "/json/version")
    async with websockets.connect(info["webSocketDebuggerUrl"]) as ws:
        await ws.send(json.dumps({"id": 1, "method": "Browser.close"}))
        try:
            await asyncio.wait_for(ws.recv(), timeout=3)
        except Exception:
            pass


def pick_rooms() -> tuple[str, str]:
    """(房主已加入的进行中房, 参与者未加入的进行中房)"""
    from app.config import load_settings
    from app.db.pool import get_conn, init_pool

    init_pool(load_settings().database_url)
    with get_conn() as conn:
        host_room = conn.execute(
            """SELECT r.id FROM rooms r JOIN users u ON u.id = r.host_id
               WHERE r.status='active' AND u.email=%s ORDER BY r.created_at DESC LIMIT 1""",
            (HOST_EMAIL,)).fetchone()
        free_room = conn.execute(
            """SELECT r.id FROM rooms r
               WHERE r.status='active'
                 AND NOT EXISTS (SELECT 1 FROM room_members m JOIN users u ON u.id=m.user_id
                                 WHERE m.room_id=r.id AND u.email=%s)
               ORDER BY r.created_at DESC LIMIT 1""",
            (PART_EMAIL,)).fetchone()
    return (host_room[0] if host_room else ""), (free_room[0] if free_room else "")


async def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="演示台本 UI 自检")
    parser.add_argument("--base-url", default="http://localhost:5173")
    parser.add_argument("--guest-port", type=int, default=9224)
    parser.add_argument("--user-port", type=int, default=9225)
    parser.add_argument("--skip-behaviour", action="store_true")
    parser.add_argument("--keep-chrome", action="store_true")
    args = parser.parse_args(argv)
    base = args.base_url.rstrip("/")
    shots = os.path.join(os.environ.get("TEMP", "."), "lg_runbook_shots")
    chrome: list[subprocess.Popen] = []

    host_room, free_room = pick_rooms()
    print(f"目标：房主房 {host_room or '（无）'}，参与者可申请的房 {free_room or '（无）'}")

    try:
        chrome.append(launch(args.guest_port, "guest"))
        chrome.append(launch(args.user_port, "user"))
        for port in (args.guest_port, args.user_port):
            info = wait_cdp(port)
            print(f"  [i] CDP {port} 就绪：{info['Browser']}")

        # ---------------- A. 未登录（台本 §0/§1/§2 的公开面） ----------------
        async with Page(args.guest_port) as guest:
            await guest.goto(f"{base}/", 3.0)
            # 侧栏默认收起（台本 §2 就写了要展开）——先展开再核标签
            await guest.js("""(async () => { const b=[...document.querySelectorAll('button')].find(x=>(x.getAttribute('title')||'').includes('侧边栏')); if(b) b.click(); await new Promise(r=>setTimeout(r,400)); return true; })()""")
            g = await probe(guest)
            check("未登录·顶栏有「大屏」「登录」「注册」",
                  all(has(g, t) for t in ("大屏", "登录", "注册")),
                  f"→ buttons/links {[t for t in ('大屏','登录','注册') if not has(g, t)] or '全在'}")
            check("未登录·侧栏四项（返回主页 / 我的房间 / 邀请码加入 / 创建房间）",
                  all(has(g, t) for t in ("返回主页", "我的房间", "邀请码加入", "创建房间")),
                  f"→ {[t for t in ('返回主页','我的房间','邀请码加入','创建房间') if not has(g, t)] or '全在'}")
            # 打开大屏面板：未登录只读
            await guest.js("""(async () => { const b=[...document.querySelectorAll('button')].find(x=>x.textContent.trim()==='大屏'); if(b) b.click(); await new Promise(r=>setTimeout(r,600)); return true; })()""")
            gp = await probe(guest)
            panel_open = await set_drawer(guest, True)
            gp = await probe(guest)
            online_hit = re.search(r"\d+ 人在线", gp["bodyText"])
            sub = {"面板打开": panel_open, "标题": has(gp, "大屏"), "在线数": online_hit is not None,
                   "只读提示": "登录后可以发言" in gp["bodyText"], "去登录": has(gp, "去登录")}
            check("未登录·大屏面板：标题 + 在线数 + 只读提示 + 去登录",
                  all(sub.values()),
                  "→ 逐项 {}；在线数 {}".format(sub, online_hit.group(0) if online_hit else None))
            check("未登录·大屏输入区是只读（没有输入框，只有去登录）",
                  not has(gp, "对所有人说一句") and "登录后可以发言" in gp["bodyText"],
                  "→ 无输入框且给了登录引导" if "登录后可以发言" in gp["bodyText"] else "→ 未见到只读提示")
            await set_drawer(guest, False)   # 收起，别影响后面截图
            await guest.shot(os.path.join(shots, "a-guest-home-and-panel.png"))

            # ---------------- B. 参与者：房卡按钮（台本 S3 / §2） ----------------
            if free_room:
                await guest.goto(f"{base}/", 2.0)   # 未登录也能看到「申请加入」
                g2 = await probe(guest)
                check("未登录/非成员·房卡按钮「申请加入」可见", has(g2, "申请加入"),
                      "→ 房卡按钮存在" if has(g2, "申请加入") else "→ 未找到")

        # ---------------- C. 房主：建房页 / 交流页 / 抽屉（台本 S2 / S4 / S6 / S7 / §2） ----------------
        async with Page(args.user_port) as user:
            who = await login(user, base, HOST_EMAIL)
            check("房主登录", who.get("status") == 200, f"→ {who}")
            await user.goto(f"{base}/rooms/new", 2.5)
            c = await probe(user)
            check("建房页·标题「创建一个学习讨论室」+ 字段与按钮",
                  has(c, "创建一个学习讨论室") and all(has(c, t) for t in ("主题", "标题", "创建房间")),
                  f"→ headings={c['headings'][:2]} buttons={[b for b in c['buttons'] if b][:6]}")
            await user.shot(os.path.join(shots, "b-create-room.png"))

            if host_room:
                # 告知条只在「没记住已读」时出现（TranscribeNotice 把已读存在 localStorage）：
                # 先清标记再进房，否则 profile 复用时会因为上一次点过「知道了」而看不到告知条。
                await user.js("window.localStorage.removeItem('lg.transcribe.notice.dismissed')")
                await user.goto(f"{base}/rooms/{host_room}/live", 8.5)
                r = await probe(user)
                check("交流页·控制坞五件（麦克风 / 摄像头 / 共享屏幕 / 取得焦点 / 结束房间）",
                      all(has(r, t) for t in ("麦克风", "摄像头", "共享屏幕", "结束房间")),
                      f"→ 缺 {[t for t in ('麦克风','摄像头','共享屏幕','结束房间') if not has(r, t)] or '无'}；dock 文案 {[b for b in r['buttons'] if b][:8]}")
                seat_hit = re.search(r"\d+ / \d+ 成员", r["bodyText"])
                check("交流页·状态条「N / M 成员」",
                      seat_hit is not None,
                      "→ {!r}".format(seat_hit.group(0) if seat_hit else None))
                chip_hit = re.search(r"转写：(开启|未开启)", r["bodyText"])
                check("交流页·转写芯片「转写：开启 / 未开启」",
                      chip_hit is not None,
                      "→ 命中 {!r}".format(chip_hit.group(0) if chip_hit else None))
                check("交流页·转写告知条与「知道了」",
                      "关掉麦克风即不参与转写" in r["bodyText"] and has(r, "知道了"),
                      "→ 告知条文案与按钮都在" if "关掉麦克风即不参与转写" in r["bodyText"] else "→ 未见到告知条")
                # 抽屉：讨论 / 成员 / 邀请
                await user.js("""(async () => { const b=[...document.querySelectorAll('button')].find(x=>x.textContent.includes('讨论与成员')); if(b) b.click(); await new Promise(r=>setTimeout(r,600)); return true; })()""")
                d1 = await probe(user)
                check("抽屉·三个 tab（讨论 / 成员 / 邀请）",
                      all(has(d1, t) for t in ("讨论", "成员", "邀请")),
                      f"→ tabs {[b for b in d1['buttons'] if b][:10]}")
                await set_panel_tab(user, "成员")
                d2 = await probe(user)
                check("抽屉·成员 tab：移出 / 设为协管 / 给焦点",
                      all(has(d2, t) for t in ("移出", "设为协管")),
                      f"→ 缺 {[t for t in ('移出','设为协管','给焦点') if not has(d2, t)] or '无'}")
                await set_panel_tab(user, "邀请")
                d3 = await probe(user)
                # 两种合法状态：还没生成码（生成邀请码 + 有效期 + 可用次数）／已有码（码行 + 复制链接）
                fresh = has(d3, "生成邀请码") and has(d3, "有效期") and has(d3, "可用次数")
                existing = has(d3, "复制链接") and has_re(d3, r"[A-Z0-9]{6}")
                check("抽屉·邀请 tab：生成邀请码 / 有效期 / 可用次数（或已有码 + 复制链接）",
                      fresh or existing,
                      "→ 生成态 {}／已有码态 {}".format(fresh, existing))
                check("房主·交流页没有「大屏」按钮（cp-8 修的口径）",
                      not any(b == "大屏" for b in r["buttons"]),
                      f"→ header 按钮 {[b for b in r['buttons'] if b][:6]}")
                await user.shot(os.path.join(shots, "c-host-live-drawer.png"))

            # ---------------- D. 超管：后台 + 隐身（台本 S10 / S11） ----------------
            who_admin = await login(user, base, ADMIN_EMAIL)
            check("超管登录", who_admin.get("role") == "superadmin", f"→ {who_admin}")
            await user.goto(f"{base}/", 2.5)
            await user.js("""(async () => { const b=[...document.querySelectorAll('button')].find(x=>(x.getAttribute('title')||'').includes('侧边栏')); if(b) b.click(); await new Promise(r=>setTimeout(r,400)); return true; })()""")
            a1 = await probe(user)
            check("超管·侧栏多一项「管理后台」，顶栏有「大屏」",
                  has(a1, "管理后台") and has(a1, "大屏"),
                  f"→ 侧栏 {a1['links'][:6]}")
            opened = await set_drawer(user, True)
            a1b = await probe(user)
            check("登录态·大屏输入框与「发布」",
                  opened and has(a1b, "对所有人说一句") and has(a1b, "发布") and "0 / 500" in a1b["bodyText"],
                  f"→ 占位符 {[p for p in a1b['placeholders'] if p]}；发布按钮 {'在' if has(a1b, '发布') else '缺'}")
            await set_drawer(user, False)
            await user.goto(f"{base}/admin", 3.0)
            t0 = time.time()
            resolved = await wait_until(
                user,
                "document.querySelectorAll('.admin-table tbody tr').length > 0 || !!document.querySelector('.empty') || !!document.querySelector('.admin-guard')",
                30)
            a2 = await probe(user)
            rows_n = int(await user.js("document.querySelectorAll('.admin-table tbody tr').length") or 0)
            print(f"  [i] 后台房间分区：{time.time()-t0:.1f}s 解析完成（{rows_n} 行）")
            if not resolved:
                print("  [!] 超时时页面片段：", a2["bodyText"][:200])
            check("后台·房间表已加载出行", rows_n > 0, f"→ {rows_n} 行；解析={'是' if resolved else '超时'}")
            check("后台·标题 + 四分区 tab",
                  has(a2, "管理后台") and all(has(a2, t) for t in ("房间", "用户", "纪要", "审计")),
                  f"→ tabs {[b for b in a2['buttons'] if b][:10]}")
            check("后台·房间表头 8 列",
                  all(has(a2, t) for t in ("房主", "状态", "待批", "创建", "动作")),
                  f"→ tableHeads {a2['tableHeads']}")
            check("后台·三动作按钮（结束 / 纪要 / 删除）+ 搜索框占位",
                  all(has(a2, t) for t in ("结束", "纪要", "删除")) and any("搜房间" in p for p in a2["placeholders"]),
                  f"→ placeholders {[p for p in a2['placeholders'] if p]}")
            check("后台·分页与刷新",
                  has(a2, "下一页") and has(a2, "刷新"),
                  f"→ 缺 {[t for t in ('下一页','刷新','上一页') if not has(a2, t)] or '无'}")
            confirm_ok = await user.js("""(async () => {
                const b=[...document.querySelectorAll('button')].find(x=>x.textContent.trim()==='删除');
                if(!b) return false;
                b.click(); await new Promise(r=>setTimeout(r,400));
                const seen = document.body.innerText.includes('确认删除？不可恢复');
                const cancel=[...document.querySelectorAll('button')].find(x=>x.textContent.trim()==='取消');
                if(cancel) cancel.click();
                await new Promise(r=>setTimeout(r,300));
                return seen; })()""")
            check("后台·删除行内二次确认文案（点了「取消」，不真删）", bool(confirm_ok),
                  "→ 出现「确认删除？不可恢复」并已点「取消」" if confirm_ok else "→ 没找到删除按钮或确认文案")
            await set_panel_tab(user, "用户")
            t1 = time.time()
            await wait_until(
                user,
                "document.querySelectorAll('.admin-table tbody tr').length > 0 || !!document.querySelector('.empty') || !!document.querySelector('.admin-guard')",
                30)
            a3 = await probe(user)
            users_ok = int(await user.js("document.querySelectorAll('.admin-table tbody tr').length") or 0) > 0
            print(f"  [i] 后台用户分区：{time.time()-t1:.1f}s 解析完成（{'有行' if users_ok else '空/未解析'}）")
            check("后台·用户分区「只看在线」与「最后活跃」列",
                  users_ok and has(a3, "只看在线") and has(a3, "最后活跃"),
                  f"→ 缺 {[t for t in ('只看在线','最后活跃') if not has(a3, t)] or '无'}")
            await user.shot(os.path.join(shots, "d-admin-page.png"))

            if host_room:
                await user.goto(f"{base}/rooms/{host_room}/live", 8)
                s, connected = await probe_when(user, "!!document.querySelector('.live-superadmin-chip')", 28)
                check("超管·隐身标识与只读控制坞",
                      connected and has(s, "管理视角 · 隐身") and all(has(s, t) for t in ("离开", "结束房间")),
                      f"→ dock {[b for b in s['buttons'] if b][:8]}")
                check("超管·没有麦克风 / 摄像头 / 共享 / 举手控件",
                      not any(has(s, t) for t in ("麦克风", "摄像头", "共享屏幕")),
                      f"→ 命中 {[t for t in ('麦克风','摄像头','共享屏幕') if has(s, t)] or '无（正确）'}")
                check("超管·顶部隐身提示条",
                      "隐身方式在场" in s["bodyText"] and "不发布音视频" in s["bodyText"],
                      "→ 提示条文案在" if "隐身方式在场" in s["bodyText"] else "→ 未见到提示条")
                await user.shot(os.path.join(shots, "e-admin-in-room.png"))

        print(f"  [i] 截图目录：{shots}")
    finally:
        if not args.keep_chrome:
            for port in (args.guest_port, args.user_port):
                try:
                    await close_browser(port)
                    print(f"  [i] Browser.close {port}")
                except Exception:
                    pass

    print("\n未覆盖（需人工 / 额外进程，不是漏测）：共享屏幕的「选整个屏幕」弹窗、录屏本身、"
          "真实语音转写气泡（需 agents.bat + STT）、首次连 LiveKit 换区耗时、演示后清理与提交包命名。")
    total = CHECKS
    if FAILURES:
        print(f"\nFAIL {len(FAILURES)}/{total} — 失败项：{', '.join(FAILURES)}")
        return 1
    print(f"\nPASS {total}/{total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main(sys.argv[1:])))
