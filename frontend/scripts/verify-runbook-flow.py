"""演示台本**行为流**自检（r012 收尾）：用真浏览器把台本 S2→S8 的主流程真跑一遍。

与 `verify-runbook-ui.py` 的分工：
- `verify-runbook-ui.py`：**文案与控件**在不在（四角色页面逐条比对）；
- 本脚本：**行为**对不对（建房 → 申请 → 批准自动进房 → 群聊 → 举手给焦点 → 邀请码 → 移出 → 结束 → 大屏跨端），
  每一步都断言「观察判据」里写的东西（系统消息原文、人数、自动跳转、对方掉线…）。

用法（先 `dev.bat` 起 8000 + 5173）：
  python frontend/scripts/verify-runbook-flow.py
  python frontend/scripts/verify-runbook-flow.py --keep-chrome     # 排障：跑完留浏览器

判据：逐条 `[OK]/[FAIL]`，末尾 `PASS n/n`；任一条不符非 0 退出。
依赖：`websockets` + 本机 Chrome；零新依赖。三个隔离 Chrome（房主 / 参与者 / 受邀客人），结束时一律 `Browser.close`。
副作用：新建**一个临时房**（标题前缀 `台本自检`）、两条账号（参与者、客人）与一条邀请码；跑完房间被「结束」（不删）。
未覆盖（需人工）：共享屏幕的「选整个屏幕」弹窗、录屏本身、真实语音转写气泡（需 `agents.bat` + STT）、首次连 LiveKit 换区耗时。

事实源：`docs/00-project/demo-runbook.md` §3（S1~S12 逐步脚本）。
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
import uuid

CHROME = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
          r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"]
PASSWORD = "demo1234"
HOST_EMAIL = "host@example.com"
PROFILE_ROOT = os.path.join(os.environ.get("TEMP", "."), "lg_runbook_flow")

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
        # headless 窗口永不聚焦 → react-query 会暂停轮询（`refetchIntervalInBackground: false`），
        # 于是「服务端新写入的系统消息」永远等不到。用 CDP 把这一页模拟成前台聚焦，
        # 与人手演示时的真实状态一致。
        await self.call("Page.bringToFront")
        await self.call("Emulation.setFocusEmulationEnabled", enabled=True)
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

    async def text(self) -> str:
        return str(await self.js("document.body.innerText.replace(/\\s+/g, ' ')") or "")

    async def url(self) -> str:
        return str(await self.js("location.href") or "")

    async def shot(self, path: str) -> str:
        out = await self.call("Page.captureScreenshot", format="png")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(base64.b64decode(out["data"]))
        return path


async def wait_for(page: Page, expression: str, timeout: float = 15.0, interval: float = 0.4) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if await page.js(expression):
                return True
        except Exception:
            pass
        await asyncio.sleep(interval)
    return False


async def login(page: Page, base: str, email: str) -> int:
    await page.goto(f"{base}/login", 2.2)
    return int(await page.js("""(async () => {
      const r = await fetch('/api/auth/login', {method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({email: %s, password: %s})});
      return r.status; })()""" % (json.dumps(email), json.dumps(PASSWORD))) or 0)


async def register(page: Page, base: str, name: str) -> str:
    """台本 S7 的「或新注册一个」路径（注册即登录）。"""
    email = f"runbook-{uuid.uuid4().hex[:8]}@example.com"
    await page.goto(f"{base}/login", 2.2)
    status = await page.js("""(async () => {
      const r = await fetch('/api/auth/register', {method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({email: %s, displayName: %s, password: %s})});
      return r.status; })()""" % (json.dumps(email), json.dumps(name), json.dumps(PASSWORD)))
    assert status == 201, f"注册失败：{status}"
    return name


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
    async with websockets.connect(http_json(port, "/json/version")["webSocketDebuggerUrl"]) as ws:
        await ws.send(json.dumps({"id": 1, "method": "Browser.close"}))
        try:
            await asyncio.wait_for(ws.recv(), timeout=3)
        except Exception:
            pass


# ------------------------------------------------------------------ 页面动作小工具
async def set_input(page: Page, selector: str, value: str) -> bool:
    return bool(await page.js("""(() => {
      const el = document.querySelector(%s);
      if (!el) return false;
      const proto = el.tagName === 'TEXTAREA' ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
      Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, %s);
      el.dispatchEvent(new Event('input', { bubbles: true }));
      return true; })()""" % (json.dumps(selector), json.dumps(value))))


async def click_text(page: Page, text: str, scope: str = "document") -> bool:
    return bool(await page.js("""(() => {
      const root = %s === 'document' ? document : document.querySelector(%s);
      if (!root) return false;
      const btn = [...root.querySelectorAll('button, a')].find(x => (x.innerText || '').trim().includes(%s));
      if (!btn) return false;
      btn.click(); return true; })()""" % (json.dumps("document"), json.dumps(scope), json.dumps(text))))


async def click_in_row(page: Page, row_contains: str, button_text: str, scope: str = "aside.live-drawer") -> bool:
    """在**包含某段文字的那一行**里点按钮（抽屉里有多行、每行都有「移出」，不能盲点第一个）。"""
    return bool(await page.js("""(() => {
      const root = %s === 'document' ? document : document.querySelector(%s);
      if (!root) return false;
      const holders = [...root.querySelectorAll('*')].filter((el) =>
        (el.innerText || '').includes(%s) && [...el.querySelectorAll('button')].some((b) => (b.innerText || '').includes(%s)));
      const target = holders.sort((a, b) => a.innerText.length - b.innerText.length)[0];
      if (!target) return false;
      const btn = [...target.querySelectorAll('button')].find((b) => (b.innerText || '').includes(%s));
      btn.click(); return true; })()""" % (json.dumps(scope), json.dumps(scope), json.dumps(row_contains),
                                            json.dumps(button_text), json.dumps(button_text))))


async def discussion_contains(page: Page, text: str, timeout: float = 8.0) -> bool:
    """切到「讨论」tab 再等某段文字出现（抽屉只有当前 tab 的内容在 DOM 里）。"""
    if not await page.js("!!document.querySelector('aside.live-drawer')"):
        await click_text(page, "讨论与成员")
        await asyncio.sleep(0.6)
    await panel_tab(page, "讨论")
    return await wait_for(page, "document.body.innerText.includes(%s)" % json.dumps(text), timeout)


async def open_members_drawer(page: Page) -> bool:
    if not await page.js("!!document.querySelector('aside.live-drawer')"):
        await click_text(page, "讨论与成员")
        await asyncio.sleep(0.6)
    return bool(await page.js("!!document.querySelector('aside.live-drawer')"))


async def panel_tab(page: Page, label: str) -> None:
    await page.js("""(async () => {
      const t = [...document.querySelectorAll('.live-drawer-tab')].find(x => x.textContent.includes(%s));
      if (t && !t.classList.contains('on')) { t.click(); await new Promise(r => setTimeout(r, 500)); }
      return true; })()""" % json.dumps(label))


async def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="演示台本行为流自检")
    parser.add_argument("--base-url", default="http://localhost:5173")
    parser.add_argument("--host-port", type=int, default=9229)
    parser.add_argument("--part-port", type=int, default=9230)
    parser.add_argument("--guest-port", type=int, default=9231)
    parser.add_argument("--keep-chrome", action="store_true")
    args = parser.parse_args(argv)
    base = args.base_url.rstrip("/")
    suffix = uuid.uuid4().hex[:6]
    title = f"台本自检 {suffix}"
    part_name = f"自检成员{suffix}"
    guest_name = f"自检客人{suffix}"
    shots = os.path.join(os.environ.get("TEMP", "."), "lg_runbook_flow_shots")

    try:
        for port, role in ((args.host_port, "host"), (args.part_port, "participant"), (args.guest_port, "guest")):
            launch(port, role)
            wait_cdp(port)
        print(f"  [i] 三个隔离 Chrome 就绪（{args.host_port}/{args.part_port}/{args.guest_port}）")

        async with Page(args.host_port) as host, Page(args.part_port) as part, Page(args.guest_port) as guest:
            # ---------------- S2 建房（UI 真走一遍） ----------------
            check("S2 房主登录", await login(host, base, HOST_EMAIL) == 200, "→ POST /api/auth/login 200")
            await host.goto(f"{base}/rooms/new", 2.5)
            await set_input(host, 'input[placeholder="这次想讨论什么"]', title)
            await click_text(host, "德国史模拟")
            await click_text(host, "创建房间")
            joined = await wait_for(host, "location.pathname.endsWith('/live')", 12)
            room_url = await host.url()
            room_id = room_url.rstrip("/").split("/")[-2] if "/rooms/" in room_url else ""
            host_text = await host.text()
            check("S2 建房后直接进交流页", joined and bool(room_id), f"→ {room_url}")
            check("S2 状态条「1 / 8 成员」与控制坞「结束房间」",
                  re.search(r"1 / 8 成员", host_text) is not None and "结束房间" in host_text,
                  "→ 命中 1 / 8 成员" if re.search(r"1 / 8 成员", host_text) else f"→ 片段 {host_text[:120]}")
            await host.shot(os.path.join(shots, "s2-room-created.png"))

            # ---------------- S3 申请 → 等待室 → 批准自动进房 ----------------
            await register(part, base, part_name)
            await part.goto(f"{base}/", 3.0)
            applied = await part.js("""(async () => {
              const card = [...document.querySelectorAll('article')].find(a => a.innerText.includes(%s));
              if (!card) return 'no-card';
              const btn = [...card.querySelectorAll('button')].find(b => b.textContent.includes('申请加入'));
              if (!btn) return 'buttons:' + [...card.querySelectorAll('button')].map(b => b.textContent.trim()).join('/');
              btn.click(); await new Promise(r => setTimeout(r, 1500)); return 'ok'; })()""" % json.dumps(title))
            part_text = await part.text()
            check("S3 参与者点「申请加入」并落到等待室",
                  applied == "ok" and "撤回申请" in part_text,
                  f"→ apply={applied}；含「撤回申请」={'撤回申请' in part_text}")
            await part.shot(os.path.join(shots, "s3-waiting.png"))

            await open_members_drawer(host)
            await panel_tab(host, "成员")
            approved = await click_text(host, "批准", "aside.live-drawer")
            auto_in = await wait_for(part, "location.pathname.endsWith('/live')", 12) if approved else False
            check("S3 房主点「批准」", approved, "→ 抽屉成员 tab 的待批行有「批准」")
            check("S3 参与者**不用点任何东西**自动进房", auto_in, f"→ 参与者当前 {await part.url()}")
            join_msg = await discussion_contains(host, f"{part_name} 加入了房间", 10)
            await panel_tab(host, "成员")
            host_text = await host.text()
            check("S3 房主端人数变 2 / 8 且房内出现「加入了房间」",
                  re.search(r"2 / 8 成员", host_text) is not None and join_msg,
                  f"→ 人数 {'2 / 8' if re.search(r'2 / 8 成员', host_text) else '不是 2 / 8'}；系统消息 {'在讨论流里' if join_msg else '未见到'}")

            # ---------------- S4 群聊 + 举手 + 给焦点 ----------------
            await open_members_drawer(part)
            await panel_tab(part, "讨论")
            await set_input(part, "textarea.chat-textarea", "台本自检：先讲第一章")
            await click_text(part, "发送", "aside.live-drawer")
            both = await discussion_contains(host, "台本自检：先讲第一章", 10)
            check("S4 群聊两端实时（房主端秒级看到同一条）", both, "→ 房主端讨论流出现该条" if both else "→ 8 秒内未出现")
            await panel_tab(host, "成员")   # 给焦点要在成员行上点，先把房主切回成员 tab
            await click_text(part, "举手")
            raiised = await wait_for(part, "[...document.querySelectorAll('button')].some(b => b.textContent.includes('放下手'))", 5)
            focus_clicked = await click_text(host, "给焦点", "aside.live-drawer")
            focus_on = await wait_for(part, "document.body.innerText.includes('退出焦点')", 8) if focus_clicked else False
            check("S4 参与者「举手」后按钮变「放下手」", raiised, "→ dock 文案切换")
            check("S4 房主「给焦点」后参与者端出现「退出焦点」（焦点生效）",
                  focus_clicked and focus_on,
                  f"→ 点给焦点={focus_clicked}；参与者端 = {await part.js('location.pathname')}")
            await click_text(part, "退出焦点")
            await asyncio.sleep(1.0)

            # ---------------- S7 邀请码：两条路径 ----------------
            await panel_tab(host, "邀请")
            await click_text(host, "生成邀请码", "aside.live-drawer")
            code = ""
            if await wait_for(host, "!!document.querySelector('.invite-code')", 6):
                code = str(await host.js("document.querySelector('.invite-code').textContent.trim()"))
            check("S7 房主生成邀请码（6 位）", bool(re.fullmatch(r"[A-Za-z0-9]{6}", code)), f"→ code={code or '未拿到'}")
            check("S7 邀请行显示「复制链接」与倒计时",
                  "复制链接" in (await host.text()) and re.search(r"\d+ 秒后过期", await host.text()) is not None,
                  "→ 复制链接 + N 秒后过期")
            # 客人：未登录打开 /join 链接
            await guest.goto(f"{base}/join?code={code}", 2.5)
            guest_text = await guest.text()
            check("S7 未登录打开邀请链接：页面有「去登录并加入」且码已预填",
                  "去登录并加入" in guest_text or "加入房间" in guest_text,
                  "→ 引导文案在" if "去登录并加入" in guest_text else f"→ 片段 {guest_text[:120]}")
            await register(guest, base, guest_name)
            await guest.goto(f"{base}/join?code={code}", 2.5)
            await click_text(guest, "加入房间")
            guest_in = await wait_for(guest, "location.pathname.endsWith('/live')", 12)
            check("S7 凭码进房（跳过等候室）", guest_in, f"→ 客人当前 {await guest.url()}")
            invite_msg = await discussion_contains(host, f"{guest_name} 通过邀请链接加入", 10)
            check("S7 房主端出现「通过邀请链接加入」",
                  invite_msg, "→ 系统消息在讨论流里" if invite_msg else "→ 未见到")

            # ---------------- S8 移出成员 + 结束房间 ----------------
            await panel_tab(host, "成员")
            seen_in_roster = await wait_for(host, "document.body.innerText.includes(%s)" % json.dumps(guest_name), 20)
            moved = False
            for _ in range(4):      # 名册靠 3 秒轮询/广播刷新，行还没出来就再等一轮
                moved = await click_in_row(host, guest_name, "移出")
                if moved:
                    break
                await asyncio.sleep(3)
            await asyncio.sleep(0.6)
            confirmed = moved and (await click_text(host, "确认", "div[role=dialog]") or await click_text(host, "确认移出"))
            kicked = await wait_for(guest, "document.body.innerText.includes('你已被移出房间')", 12) if confirmed else False
            if not moved:
                rows = await host.js("""JSON.stringify([...document.querySelectorAll('aside.live-drawer *')]
                    .filter(e => e.children.length === 0).map(e => (e.innerText || '').trim()).filter(Boolean).slice(0, 40))""")
                print("  [!] 名册行文案快照：", rows)
            check("S8 移出成员：对方端显示「你已被移出房间」", confirmed and kicked,
                  f"→ 客人出现在名册={seen_in_roster} 点到那一行={moved} 确认={confirmed}；客人端={'已掉线提示' if kicked else '未见到'}")
            await host.js("""(() => { const b = [...document.querySelectorAll('button')].find(x => x.textContent.includes('结束房间')); if (b) b.click(); return true; })()""")
            await asyncio.sleep(0.6)
            ended = await click_text(host, "结束房间", "div[role=dialog]") or await click_text(host, "确认")
            host_ended = await wait_for(host, "document.body.innerText.includes('房间已结束')", 10)
            part_ended = await wait_for(part, "document.body.innerText.includes('房间已结束')", 12)
            check("S8 结束房间：两端都变只读", ended and host_ended and part_ended,
                  f"→ 房主端={host_ended} 参与者端={part_ended}")

            # ---------------- S11 大屏跨端（全服） ----------------
            msg = f"台本自检大屏 {suffix}"
            await host.goto(f"{base}/", 2.5)
            await host.js("""(async () => { const b = [...document.querySelectorAll('button')].find(x => x.textContent.trim() === '大屏'); if (b && !document.querySelector('aside.gc-drawer.on')) b.click(); await new Promise(r => setTimeout(r, 700)); return true; })()""")
            await set_input(host, "aside.gc-drawer textarea.chat-textarea", msg)
            await click_text(host, "发布", "aside.gc-drawer")
            posted = await wait_for(host, f"document.body.innerText.includes({json.dumps(msg)})", 8)
            await part.goto(f"{base}/", 2.5)
            await part.js("""(async () => { const b = [...document.querySelectorAll('button')].find(x => x.textContent.trim() === '大屏'); if (b && !document.querySelector('aside.gc-drawer.on')) b.click(); await new Promise(r => setTimeout(r, 700)); return true; })()""")
            seen = await wait_for(part, f"document.body.innerText.includes({json.dumps(msg)})", 10)
            check("S11 大屏：房主发出后，参与者端**不刷新**即可见", posted and seen,
                  f"→ 自己端={posted} 另一端={seen}")
            await host.shot(os.path.join(shots, "s11-global-panel.png"))
            print(f"  [i] 截图目录：{shots}；临时房 {room_id}（已结束，未删）")
    finally:
        if not args.keep_chrome:
            for port in (args.host_port, args.part_port, args.guest_port):
                try:
                    await close_browser(port)
                    print(f"  [i] Browser.close {port}")
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
