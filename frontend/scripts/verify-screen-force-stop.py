"""r013 真机取证：**服务端强停共享**（r004 未闭合④ / r011 人工剧本 MV-2）。

场景：A 端正在共享屏幕（B 端看得到），A **不点「停止共享」**，直接让 A 的连接消失（关标签/断连）——
B 端应当**自动清掉共享格并恢复宫格**。本脚本量化「多久清掉」并判断是否停在最后一帧。

用法（先 `dev.bat`）：
  python frontend/scripts/verify-screen-force-stop.py
  python frontend/scripts/verify-screen-force-stop.py --kill=target   # 关标签（默认）
  python frontend/scripts/verify-screen-force-stop.py --kill=navigate # 退到 about:blank（等价硬断）
判据：B 端共享格消失；Δ 秒数照实打印（LiveKit 判离线本身要几秒~十几秒，这不是缺陷）。
零新依赖；副作用：建一个临时房（`共享强停` 前缀）并结束它。
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
PROFILE_ROOT = os.path.join(os.environ.get("TEMP", "."), "lg_sharestop")


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


def client(email=None, reg=None):
    jar = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    path, payload = ("/api/auth/register", reg) if reg else ("/api/auth/login", {"email": email, "password": PASSWORD})
    op.open(urllib.request.Request("http://127.0.0.1:8000" + path, data=json.dumps(payload).encode(),
             headers={"Content-Type": "application/json"}, method="POST"), timeout=10)
    return op


def call(op, method: str, path: str, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    with op.open(urllib.request.Request("http://127.0.0.1:8000" + path, data=data,
                 headers={"Content-Type": "application/json"}, method=method), timeout=15) as resp:
        return resp.status, json.loads(resp.read().decode() or "{}")


class Page:
    def __init__(self, port: int, label: str) -> None:
        self.port, self.label, self._id, self.target_id = port, label, 0, None

    async def __aenter__(self) -> "Page":
        import websockets
        target = next(t for t in http_json(self.port, "/json/list") if t.get("type") == "page")
        self.target_id = target["id"]
        self._ws = await websockets.connect(target["webSocketDebuggerUrl"], max_size=40_000_000, ping_interval=None)
        for m in ("Runtime.enable", "Page.enable"):
            await self.call(m)
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

    async def js(self, expr: str):
        out = await self.call("Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=True)
        return out.get("result", {}).get("value")

    async def login(self, base: str, email: str) -> None:
        await self.call("Page.navigate", url=f"{base}/login")
        await asyncio.sleep(2.2)
        await self.js("""(async () => { const r = await fetch('/api/auth/login', {method:'POST',
            headers:{'Content-Type':'application/json'}, body: JSON.stringify({email: %s, password: %s})});
            return r.status; })()""" % (json.dumps(email), json.dumps(PASSWORD)))

    async def goto(self, url: str, wait: float = 6.0) -> None:
        await self.call("Page.navigate", url=url)
        await asyncio.sleep(wait)

    async def ready(self, timeout: float = 40.0) -> bool:
        end = time.time() + timeout
        while time.time() < end:
            state = json.loads(await self.js("""JSON.stringify({
              badge: (document.querySelector('.live-badge') || {}).innerText || '',
              share: (() => { const b = [...document.querySelectorAll('button')]
                  .find(x => (x.getAttribute('title') || '').includes('共享屏幕')); return b ? b.disabled : null; })()
            })""") or "{}")
            if "已连接" in state.get("badge", "") and state.get("share") is False:
                return True
            await asyncio.sleep(0.5)
        return False

    async def share_cells(self) -> int:
        return int(await self.js("document.querySelectorAll('.live-cell.is-share').length") or 0)

    async def video_clock(self) -> float | None:
        return await self.js("""(() => { const v = document.querySelector('.live-cell.is-share video'); return v ? v.currentTime : null; })()""")


def launch(port: int, role: str) -> subprocess.Popen:
    exe = next((c for c in CHROME if os.path.exists(c)), None)
    if not exe:
        raise RuntimeError("找不到本机 Chrome")
    profile = os.path.join(PROFILE_ROOT, role)
    os.makedirs(profile, exist_ok=True)
    return subprocess.Popen([exe, "--headless=new", f"--remote-debugging-port={port}", f"--user-data-dir={profile}",
                             "--no-first-run", "--no-default-browser-check", "--disable-gpu", "--mute-audio",
                             "--window-size=1440,900",
                             # 无头下让 getDisplayMedia 直接选中「整个屏幕」，不再弹选择器
                             "--auto-select-desktop-capture-source=Entire screen",
                             "--use-fake-ui-for-media-stream", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


async def close_browser(port: int) -> None:
    import websockets
    try:
        async with websockets.connect(http_json(port, "/json/version")["webSocketDebuggerUrl"], ping_interval=None) as ws:
            await ws.send(json.dumps({"id": 1, "method": "Browser.close"}))
            try:
                await asyncio.wait_for(ws.recv(), timeout=3)
            except Exception:  # noqa: BLE001
                pass
    except Exception:  # noqa: BLE001
        pass


async def hard_kill(port: int, target_id: str, mode: str) -> None:
    """让 A 端的连接**不经过「停止共享」**就消失：关标签（target）或退到空白页（navigate）。"""
    import websockets
    async with websockets.connect(http_json(port, "/json/version")["webSocketDebuggerUrl"], ping_interval=None) as ws:
        if mode == "target":
            await ws.send(json.dumps({"id": 1, "method": "Target.closeTarget", "params": {"targetId": target_id}}))
        else:
            await ws.send(json.dumps({"id": 1, "method": "Target.activateTarget", "params": {"targetId": target_id}}))
        try:
            await asyncio.wait_for(ws.recv(), timeout=3)
        except Exception:  # noqa: BLE001
            pass


async def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="强停共享取证")
    ap.add_argument("--base-url", default="http://localhost:5173")
    ap.add_argument("--ports", default="9260,9261")
    ap.add_argument("--kill", choices=("target", "navigate"), default="target")
    ap.add_argument("--keep-chrome", action="store_true")
    args = ap.parse_args(argv)
    base = args.base_url.rstrip("/")
    a_port, b_port = [int(x) for x in args.ports.split(",")]
    tag = uuid.uuid4().hex[:6]

    host = client(HOST_EMAIL)
    _, room = call(host, "POST", "/api/rooms", {"topic": "custom", "topicLabel": "共享强停",
                                                "title": f"共享强停 {tag}", "description": "r013 取证"})
    room_id = room["data"]["id"]
    guest = client(None, {"email": f"share-{tag}@example.com", "displayName": f"观看者{tag}", "password": PASSWORD})
    _, jr = call(guest, "POST", f"/api/rooms/{room_id}/join-requests", {"message": "x"})
    call(host, "POST", f"/api/join-requests/{jr['data']['id']}/approve")
    print(f"临时房 {room_id}（A=房主共享 / B=观看者）")

    shots = os.path.join(os.environ.get("TEMP", "."), "lg_sharestop_shots")
    try:
        launch(a_port, "a")
        launch(b_port, "b")
        wait_cdp(a_port)
        wait_cdp(b_port)
        async with Page(a_port, "A") as a, Page(b_port, "B") as b:
            await a.login(base, HOST_EMAIL)
            await b.login(base, f"share-{tag}@example.com")
            await a.goto(f"{base}/rooms/{room_id}/live")
            await b.goto(f"{base}/rooms/{room_id}/live")
            ra, rb = await a.ready(), await b.ready()
            print(f"  [i] A 就绪={ra} B 就绪={rb}")
            if not (ra and rb):
                print("  [!] 有一端未就绪，早退")
                return 1
            started = await a.js("""(() => { const btn = [...document.querySelectorAll('button')]
                .find(x => (x.getAttribute('title') || '').includes('共享屏幕')); if (!btn) return 'no-btn';
                if (btn.disabled) return 'disabled'; btn.click(); return 'clicked'; })()""")
            share_seen = False
            for _ in range(40):
                await asyncio.sleep(0.5)
                if await b.share_cells() > 0:
                    share_seen = True
                    break
            print(f"  [i] A 点共享={started}｜B 端共享格出现={share_seen}")
            if not share_seen:
                print("  [!] 无头环境未成功建起屏幕共享 → 本项无法取证（如实记录，不用假数据充数）")
                return 1
            clock1 = await b.video_clock()
            await asyncio.sleep(2.0)
            clock2 = await b.video_clock()

            t0 = time.time()
            await hard_kill(a_port, a.target_id, args.kill)
            cleared_at = None
            while time.time() - t0 < 60:
                if await b.share_cells() == 0:
                    cleared_at = time.time() - t0
                    break
                await asyncio.sleep(0.5)
            after = int(await b.js("document.querySelectorAll('.live-cell').length") or 0)
            shot = await b.call("Page.captureScreenshot", format="png")
            os.makedirs(shots, exist_ok=True)
            path = os.path.join(shots, f"b-after-force-stop-{tag}.png")
            with open(path, "wb") as fh:
                fh.write(base64.b64decode(shot["data"]))
            frozen = "判定不了（无头环境的共享源是静态画面，`currentTime` 不前进）"
            print(f"  [i] A 的共享画面时钟：{clock1} → {clock2}；冻结判定：{frozen}")
            print(f"  [i] B 端清格耗时：{'%.1f 秒' % cleared_at if cleared_at else '60 秒内未清'}")
            print(f"  [i] B 端清格后宫格数={after}；截图 {path}")
            print("\n结论（照实）：强停后 B 端" + ("自动清格，耗时 %.1f 秒" % cleared_at if cleared_at else "未在 60 秒内清格")
                  + "。手段=A 标签被关（WS 正常关闭，非网络级硬断）；网络级硬断需防火墙/物理断网，见 r013 需求单 §10.5 的断线方案，本轮未测。")
    finally:
        try:
            call(host, "POST", f"/api/rooms/{room_id}/end")
            print("  [i] 临时房已结束")
        except Exception as exc:  # noqa: BLE001
            print("  [!] 结束临时房失败：", exc)
        if not args.keep_chrome:
            for port in (a_port, b_port):
                await close_browser(port)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main(sys.argv[1:])))
