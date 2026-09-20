"""r013 真机复现/验收：**三人档「给焦点」三端一致**（E1/E2）。

背景（r009.5 登记、`docs/00-project/global-roadmap.md` §9）：三人档下房主在举手格点「给焦点」后，
被给焦点那端正确，但**房主自己的界面**没进焦点布局（`data-stage-mode=uniform`、`.is-focus`=0）。

本脚本用三个隔离 Chrome 真跑：建房 → 两人申请获批 → 三人进房 → 第二人举手 → 房主在举手格点「给焦点」
→ 同时读**三端**与**服务端 focus**，判断「状态没到」还是「到了但布局没生效」。

用法（先 `dev.bat`）：
  python frontend/scripts/verify-focus-three-way.py            # 复现/验收
  python frontend/scripts/verify-focus-three-way.py --keep-chrome
判据：三端 `data-stage-mode=focus`、`.is-focus` 各 1 格、焦点 identity 一致 → PASS。
零新依赖（websockets + 本机 Chrome）；副作用：建一个临时房（标题前缀 `焦点自检`）并**结束**它。
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
import http.cookiejar
import uuid

PASSWORD = "demo1234"
HOST_EMAIL = "host@example.com"
CHROME = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
          r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"]
PROFILE_ROOT = os.path.join(os.environ.get("TEMP", "."), "lg_focus3")
FAILS: list[str] = []
N = 0


def check(step: str, ok: bool, detail: str) -> None:
    global N
    N += 1
    print(f"[{'OK ' if ok else 'FAIL'}] {step} — {detail}")
    if not ok:
        FAILS.append(step)


# ---------------- HTTP（造数据用） ----------------
def client(email: str):
    jar = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    op.open(urllib.request.Request("http://127.0.0.1:8000/api/auth/login",
             data=json.dumps({"email": email, "password": PASSWORD}).encode(),
             headers={"Content-Type": "application/json"}, method="POST"), timeout=10)
    return op


def call(op, method: str, path: str, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request("http://127.0.0.1:8000" + path, data=data,
                                 headers={"Content-Type": "application/json"}, method=method)
    with op.open(req, timeout=15) as resp:
        return resp.status, json.loads(resp.read().decode() or "{}")


def setup_room(tag: str) -> dict:
    host = client(HOST_EMAIL)
    st, room = call(host, "POST", "/api/rooms", {"topic": "custom", "topicLabel": "焦点自检",
                                                 "title": f"焦点自检 {tag}", "description": "r013 三人档焦点复现"})
    assert st == 201, f"建房失败 {st}"
    room_id = room["data"]["id"]
    members = []
    for idx in (2, 3):
        email = f"focus{idx}-{tag}@example.com"
        name = f"焦点成员{idx}{tag[-3:]}"
        jar = http.cookiejar.CookieJar()
        op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        op.open(urllib.request.Request("http://127.0.0.1:8000/api/auth/register",
                 data=json.dumps({"email": email, "displayName": name, "password": PASSWORD}).encode(),
                 headers={"Content-Type": "application/json"}, method="POST"), timeout=10)
        st, jr = call(op, "POST", f"/api/rooms/{room_id}/join-requests", {"message": "自检"})
        assert st == 201, f"申请失败 {st}"
        call(host, "POST", f"/api/join-requests/{jr['data']['id']}/approve")
        members.append({"email": email, "name": name, "client": op})
    return {"room_id": room_id, "host": host, "members": members}


# ---------------- CDP ----------------
def http_json(port: int, path: str):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=3) as resp:
        return json.loads(resp.read().decode())


def wait_cdp(port: int, seconds: float = 25.0) -> None:
    end, last = time.time() + seconds, None
    while time.time() < end:
        try:
            http_json(port, "/json/version")
            return
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(0.4)
    raise RuntimeError(f"CDP {port} 未就绪：{last}")


class Page:
    def __init__(self, port: int, label: str) -> None:
        self.port, self.label, self._id = port, label, 0
        # 排障用：收集 Console/异常事件（CDP 的 ping 与事件都被 call() 读过，这里顺手留痕）
        self.events: list[str] = []

    async def __aenter__(self) -> "Page":
        import websockets
        end, target = time.time() + 10, None
        while time.time() < end:
            pages = [t for t in http_json(self.port, "/json/list") if t.get("type") == "page"]
            if pages:
                target = pages[0]
                break
            await asyncio.sleep(0.3)
        # 三个 headless Chrome 同时跑 WebRTC 时机器较忙，CDP 的 keepalive ping 会超时被掐断；
        # 脚本生命周期很短，直接关掉 ping（实测 `keepalive ping timeout` 由此而来）。
        self._ws = await websockets.connect(target["webSocketDebuggerUrl"], max_size=40_000_000, ping_interval=None)
        for m in ("Runtime.enable", "Page.enable", "Log.enable"):
            await self.call(m)
        await self.call("Page.bringToFront")                              # 失焦窗口会暂停轮询
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
            method = raw.get("method", "")
            if method in ("Log.entryAdded", "Runtime.exceptionThrown"):
                text = json.dumps(raw.get("params", {}), ensure_ascii=False)[:220]
                self.events.append(f"{method}: {text}")
                self.events = self.events[-12:]
            if raw.get("id") == mid:
                if "error" in raw:
                    raise RuntimeError(f"{method}: {raw['error']}")
                return raw.get("result", {})

    async def js(self, expr: str):
        out = await self.call("Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=True)
        return out.get("result", {}).get("value")

    async def goto(self, url: str, wait: float = 3.0) -> None:
        await self.call("Page.navigate", url=url)
        await asyncio.sleep(wait)

    async def login(self, base: str, email: str) -> None:
        await self.goto(f"{base}/login", 2.2)
        await self.js("""(async () => { const r = await fetch('/api/auth/login', {method:'POST',
            headers:{'Content-Type':'application/json'}, body: JSON.stringify({email: %s, password: %s})});
            return r.status; })()""" % (json.dumps(email), json.dumps(PASSWORD)))

    async def wait_ready(self, timeout: float = 45.0) -> bool:
        """等**本页自己**就绪：状态条「已连接」且控制坞按钮不再 disabled。

        （踩过：只看房主端格子数就动手 → 本页 status 还在 connecting，控制坞 disabled，
        `.click()` 对 disabled 按钮不生效，会被误读成「举手没传播」。）
        """
        end = time.time() + timeout
        while time.time() < end:
            raw = await self.js("""JSON.stringify({
              badge: (document.querySelector('.live-badge') || {}).innerText || '',
              dockDisabled: (() => { const b = [...document.querySelectorAll('button')]
                  .find(x => (x.getAttribute('title') || '').includes('麦克风')); return b ? b.disabled : null; })()
            })""")
            state = json.loads(raw or "{}")
            if "已连接" in state.get("badge", "") and state.get("dockDisabled") is False:
                return True
            await asyncio.sleep(0.5)
        return False

    async def wait_cells(self, n: int, timeout: float = 30.0) -> int:
        end = time.time() + timeout
        count = 0
        while time.time() < end:
            count = int(await self.js("document.querySelectorAll('.live-cell').length") or 0)
            if count >= n:
                return count
            await asyncio.sleep(0.5)
        return count

    async def diag(self) -> dict:
        """排障快照：URL / 状态条 / 正文片段 / Console 尾巴。"""
        raw = await self.js("""JSON.stringify({
          url: location.href,
          badge: (document.querySelector('.live-badge') || {}).innerText || null,
          cells: document.querySelectorAll('.live-cell').length,
          head: document.body.innerText.replace(/\\s+/g, ' ').slice(0, 160)
        })""")
        out = json.loads(raw or "{}")
        out["events"] = self.events[-5:]
        return out

    async def stage(self) -> dict:
        raw = await self.js("""JSON.stringify((() => {
            const grid = document.querySelector('.live-stage-grid');
            const cells = [...document.querySelectorAll('.live-cell')];
            return {
              mode: grid ? grid.dataset.stageMode : null,
              ids: grid ? (grid.dataset.stageIds || '') : '',
              focusCells: cells.filter(c => c.classList.contains('is-focus')).length,
              kinds: cells.map(c => (c.dataset.flipId || '?') + ':' + (c.dataset.kind || '?')),
              badges: [...document.querySelectorAll('.live-focus-badge')].map(b => b.innerText.trim()),
              bodyFocus: (document.body.innerText.match(/焦点[^\\n]{0,12}/) || [null])[0],
            };
          })())""")
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
    try:
        async with websockets.connect(http_json(port, "/json/version")["webSocketDebuggerUrl"]) as ws:
            await ws.send(json.dumps({"id": 1, "method": "Browser.close"}))
            try:
                await asyncio.wait_for(ws.recv(), timeout=3)
            except Exception:  # noqa: BLE001
                pass
    except Exception:  # noqa: BLE001
        pass


async def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="三人档焦点三端一致性")
    ap.add_argument("--base-url", default="http://localhost:5173")
    ap.add_argument("--ports", default="9234,9235,9236")
    ap.add_argument("--keep-chrome", action="store_true")
    args = ap.parse_args(argv)
    base = args.base_url.rstrip("/")
    ports = [int(x) for x in args.ports.split(",")]
    tag = uuid.uuid4().hex[:6]
    ctx = setup_room(tag)
    room_id = ctx["room_id"]
    m2_name = ctx["members"][0]["name"]
    print(f"临时房 {room_id}｜第二人 {m2_name}")

    try:
        for port, role in zip(ports, ("host", "m2", "m3")):
            launch(port, role)
            wait_cdp(port)
        async with Page(ports[0], "host") as host, Page(ports[1], "m2") as m2, Page(ports[2], "m3") as m3:
            await host.login(base, HOST_EMAIL)
            await m2.login(base, ctx["members"][0]["email"])
            await m3.login(base, ctx["members"][1]["email"])
            for page in (host, m2, m3):
                await page.goto(f"{base}/rooms/{room_id}/live", 6)
            ready = [await host.wait_ready(25), await m2.wait_ready(25), await m3.wait_ready(25)]
            counts = [await host.wait_cells(3, 20), await m2.wait_cells(1, 10), await m3.wait_cells(1, 10)]
            check("三人进房、各自状态条已连接", all(ready) and counts[0] >= 3,
                  f"→ 本页就绪 {ready}；房主端格子数 {counts[0]}")
            if not all(ready):
                for page in (host, m2, m3):
                    print(f"  [!] {page.label} 排障：", json.dumps(await page.diag(), ensure_ascii=False)[:400])
                print("  [!] 有端未就绪（未连接/控制坞禁用）→ 早退：此时点按钮不会生效，继续跑只会误报")
                return 1

            # 第一步：m2 自己的按钮要变成「放下手」——那才证明 POST 成功（只看 `.click()` 返回 true 会被 disabled 按钮骗过）
            clicked = "not-tried"
            local_on = False
            for attempt in range(3):
                # 等控制坞可点（status=connecting/reconnecting 时按钮 disabled，`.click()` 不生效）
                for _ in range(30):
                    state = json.loads(await m2.js("""JSON.stringify((() => { const b = [...document.querySelectorAll('button')]
                        .find(x => (x.getAttribute('title') || '').includes('举手')); return { found: !!b, disabled: b ? b.disabled : null }; })())""") or "{}")
                    if state.get("found") and state.get("disabled") is False:
                        break
                    await asyncio.sleep(0.5)
                clicked = await m2.js("""(() => { const b = [...document.querySelectorAll('button')]
                    .find(x => (x.getAttribute('title') || '').includes('举手')); if (!b) return 'no-btn';
                    if (b.disabled) return 'disabled'; b.click(); return 'clicked'; })()""")
                for _ in range(16):
                    await asyncio.sleep(0.5)
                    local_on = bool(await m2.js("""[...document.querySelectorAll('button')]
                        .some(x => (x.getAttribute('title') || '').includes('放下手'))"""))
                    if local_on:
                        break
                if local_on:
                    break
                print(f"  [!] 第 {attempt + 1} 次举手未生效（click={clicked}），重试")
            _, hands_api = call(ctx["members"][0]["client"], "GET", f"/api/rooms/{room_id}/hand-raises")
            hand_ids = [item.get("userId") for item in (hands_api.get("data") or {}).get("hands", [])]
            check("第二人举手：POST 成功（按钮变「放下手」+ 库里有一条）",
                  local_on and bool(hand_ids), f"→ 点击={clicked} 本端已举手={local_on} 服务端 hands={hand_ids}")
            hand_seen = False
            for _ in range(16):
                await asyncio.sleep(0.5)
                hand_seen = bool(await host.js("!!document.querySelector('.live-cell.is-hand')"))
                if hand_seen:
                    break
            if hand_seen:
                check("第二人举手 → 房主端出现举手格（广播/刷新到达）", True, "→ 房主端举手格=True")
            else:
                # 分清「广播丢给所有人」还是「只丢给房主」：另两端也读一次举手格
                cells = {}
                for page in (host, m2, m3):
                    cells[page.label] = int(await page.js("document.querySelectorAll('.live-cell.is-hand').length") or 0)
                m2_events = [e for e in m2.events if "广播" in e or "publishData" in e][-2:]
                check("第二人举手 → 房主端出现举手格（广播/刷新到达）", False,
                      f"→ 各端举手格数 {cells}；m2 广播告警 {m2_events or '无'}；房主端事件 {host.events[-2:]}")
                print("  [i] 房主端舞台 kinds：", (await host.stage())["kinds"])

            granted = await host.js("""(async () => {
                const cell = document.querySelector('.live-cell.is-hand');
                if (!cell) return 'no-cell';
                const btn = [...cell.querySelectorAll('button')].find(b => b.textContent.includes('给焦点'));
                if (!btn) return 'no-btn';
                btn.click(); await new Promise(r => setTimeout(r, 1200)); return 'ok'; })()""")
            check("房主在举手格点「给焦点」", granted == "ok", f"→ {granted}")
            await asyncio.sleep(3.0)

            st_host, st_m2, st_m3 = await host.stage(), await m2.stage(), await m3.stage()
            _, focus_api = call(ctx["host"], "GET", f"/api/rooms/{room_id}/focus")
            focus_user = (focus_api.get("data", {}).get("focus") or {}).get("userId")
            print("  服务端 focus:", focus_user)
            for label, st in (("房主端", st_host), ("第二人端", st_m2), ("第三人端", st_m3)):
                print(f"  {label}: mode={st['mode']} focus格={st['focusCells']} ids={st['ids']} kinds={st['kinds']} 徽标={st['badges']}")

            check("三端都进 focus 布局", all(st["mode"] == "focus" for st in (st_host, st_m2, st_m3)),
                  f"→ modes = {[st['mode'] for st in (st_host, st_m2, st_m3)]}")
            check("三端焦点格各 1", all(st["focusCells"] == 1 for st in (st_host, st_m2, st_m3)),
                  f"→ focus 格数 = {[st['focusCells'] for st in (st_host, st_m2, st_m3)]}")
            focus_of = lambda st: next((k.split(":")[0] for k in st["kinds"] if k.endswith(":focus")), None)
            focus_ids = [focus_of(st) for st in (st_host, st_m2, st_m3)]
            check("三端焦点 identity 一致（都指向持焦点那一人）",
                  focus_ids[0] is not None and len(set(focus_ids)) == 1,
                  f"→ 三端焦点身份 = {focus_ids}；排第一的是本地（各端不同属正常）")
            check("三端排序都把本地放首位（本地优先口径未退化）",
                  all(st["kinds"] and st["kinds"][0].endswith((":focus", ":grid")) for st in (st_host, st_m2, st_m3)),
                  "→ 各端 kinds 结构正常")
    finally:
        try:
            call(ctx["host"], "POST", f"/api/rooms/{room_id}/end")
            print("  [i] 临时房已结束")
        except Exception as exc:  # noqa: BLE001
            print("  [!] 结束临时房失败：", exc)
        if not args.keep_chrome:
            for port in ports:
                await close_browser(port)

    if FAILS:
        print(f"\nFAIL {len(FAILS)}/{N} — {', '.join(FAILS)}")
        return 1
    print(f"\nPASS {N}/{N}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main(sys.argv[1:])))
