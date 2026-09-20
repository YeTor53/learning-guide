"""r009.5 取证脚本：舞台几何/动效量测 + 声波证据 + 教学流程复跑。

用途（r009.5 补正轮 E9/E10/E12）：把 r009 需求单里 E0（变化动效）与 E11（声波）
的实测数字补上，并复跑 r008/r009 的使用者流程（邀请 / 焦点 / 纪要）供教学页引用。

运行（本机，Playwright 在 conda base，**不新增仓库依赖**）：
    C:\ProgramData\miniconda3\python.exe frontend/scripts/verify-stage-motion.py

前置：后端 http://localhost:8000（uvicorn，无 --reload）+ 前端 http://localhost:5173（vite dev）已在跑。

纪律（与仓库既有约定一致）：
- 无头运行，必加 `--mute-audio`；**不发布麦克风**（只授权 camera：默认「麦克风开」的发布请求会失败，
  因此本脚本**不产生任何音频**，也拿不到非零电平——E11 数值序列如实标未取证）；
- 不抢前台、不按进程名杀进程；截图落 %TEMP%\lg_r009.5\。
"""
from __future__ import annotations

import json
import os
import random
import string
import sys
import time

from playwright.sync_api import sync_playwright

API = "http://localhost:8000/api"
WEB = "http://localhost:5173"
OUT = os.path.join(os.environ.get("TEMP", "/tmp"), "lg_r009.5")
SHOTS: list[str] = []


def io_open(path: str, mode: str = "w"):
    """统一 UTF-8 + LF 写文件（本机 G: 盘口径）。"""
    import io as _io

    return _io.open(path, mode, encoding="utf-8", newline="\n")

def log(*parts) -> None:
    print(*parts, flush=True)


def shot(page, name: str) -> str:
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    page.screenshot(path=path)
    SHOTS.append(name)
    log(f"    [shot] {name}")
    return path


def rand(n: int = 6) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def register(ctx, tag: str, sfx: str) -> dict:
    email = f"r0095_{tag}_{sfx}@example.com"
    payload = {"email": email, "displayName": f"r009.5{tag}", "password": "Passw0rd!23"}
    r = ctx.request.post(f"{API}/auth/register", data=json.dumps(payload), headers={"Content-Type": "application/json"})
    assert r.status == 201, f"注册失败 {r.status} {r.text()[:200]}"
    return {"email": email, "displayName": payload["displayName"], "user": json.loads(r.text())["data"]["user"]}


def create_room(ctx, sfx: str) -> str:
    body = {"topic": "custom", "topicLabel": "r009.5 动效取证", "title": f"r009.5 动效取证 {sfx}", "description": "r009.5 E0/E11 真机取证房间"}
    r = ctx.request.post(f"{API}/rooms", data=json.dumps(body), headers={"Content-Type": "application/json"})
    assert r.status == 201, f"建房失败 {r.status} {r.text()[:200]}"
    return json.loads(r.text())["data"]["id"]


def enter(page, room_id: str, *, with_camera: bool = True, wait_ms: int = 9000) -> str:
    """进房并等连接就绪；默认打开摄像头（合成测试设备）出格子。返回连接状态。"""
    page.goto(f"{WEB}/rooms/{room_id}/live", wait_until="domcontentloaded")
    deadline = time.time() + wait_ms / 1000
    state = "unknown"
    while time.time() < deadline:
        state = page.evaluate("() => (window.__lgRoom && window.__lgRoom.state) || 'none'")
        if state == "connected":
            break
        page.wait_for_timeout(300)
    if state != "connected":
        return state
    if with_camera:
        page.evaluate("async () => { try { await window.__lgRoom.localParticipant.setCameraEnabled(true) } catch (e) { return e.message } }")
    page.wait_for_timeout(2500)
    return state


def cells(page) -> list[dict]:
    return page.evaluate(
        """() => Array.from(document.querySelectorAll('.live-cell')).map((e) => {
             const r = e.getBoundingClientRect()
             return { id: e.dataset.flipId, kind: e.dataset.kind, x: +r.x.toFixed(2), y: +r.y.toFixed(2),
                      w: +r.width.toFixed(2), h: +r.height.toFixed(2), hand: e.classList.contains('is-hand'),
                      focus: e.classList.contains('is-focus') }
           })"""
    )


def main() -> int:
    sfx = rand()
    report: dict = {"sfx": sfx, "run": time.strftime("%Y-%m-%d %H:%M:%S")}
    os.makedirs(OUT, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--use-fake-device-for-media-stream",
                  "--mute-audio", "--autoplay-policy=no-user-gesture-required"],
        )
        # 关键：**不加** `--use-fake-ui-for-media-stream`（那会自动批准麦克风提示 → 会发布假麦）；
        # 只用 permissions 授权摄像头 → 默认「麦克风开」的发布被拒 → 全程无音频（见文件头纪律）
        ctxA = browser.new_context(viewport={"width": 1440, "height": 900}, permissions=["camera"])
        ctxB = browser.new_context(viewport={"width": 1440, "height": 900}, permissions=["camera"])
        ctxC = browser.new_context(viewport={"width": 1440, "height": 900}, permissions=["camera"])
        register(ctxC, "c", sfx)
        console: list[str] = []
        ctxA.on("console", lambda m: console.append(f"{m.type}: {m.text[:160]}"))

        host = register(ctxA, "host", sfx)
        room_id = create_room(ctxA, sfx)
        log(f"[setup] room={room_id} host={host['email']}")
        report["room"] = room_id

        pageA = ctxA.new_page()
        stateA = enter(pageA, room_id)
        log(f"[A] host 连接状态 = {stateA}; 格子 = {len(cells(pageA))}")
        report["connect_state"] = stateA
        report["mic_published"] = pageA.evaluate("() => window.__lgRoom.localParticipant.isMicrophoneEnabled")

        # ---------- E0 令牌 ----------
        tokens = pageA.evaluate(
            """() => { const cs = getComputedStyle(document.documentElement)
                 const names = ['--stage-move-ms','--stage-fade-ms','--hand-blink-ms','--mic-pulse-ms','--tile-fit']
                 return Object.fromEntries(names.map((n) => [n, cs.getPropertyValue(n).trim()])) }"""
        )
        log("[E0] 令牌:", json.dumps(tokens, ensure_ascii=False))
        report["tokens"] = tokens

        # ---------- E0 布局变化动效（两场景：入场重排 / 焦点切换） ----------
        rec_js = """(arg) => {
            const cell = document.querySelector(`.live-cell[data-flip-id="${arg.identity}"]`)
            if (!cell) return false
            const t0 = performance.now()
            window.__lgRec = { t0, samples: [], anims: [] }
            const loop = () => {
              const r = cell.getBoundingClientRect()
              const all = Array.from(document.querySelectorAll('.live-cell'))
              const anims = all.flatMap((e) => e.getAnimations().map((a) => (a.effect && a.effect.getTiming ? a.effect.getTiming().duration : null)))
              window.__lgRec.samples.push({ t: +(performance.now() - window.__lgRec.t0).toFixed(1),
                x: +r.x.toFixed(2), y: +r.y.toFixed(2), w: +r.width.toFixed(2), h: +r.height.toFixed(2), n: anims.length })
              for (const d of anims) if (d != null && !window.__lgRec.anims.includes(d)) window.__lgRec.anims.push(d)
              if (performance.now() - window.__lgRec.t0 < arg.ms) requestAnimationFrame(loop)
            }
            requestAnimationFrame(loop)
            return true
        }"""

        def center(c):
            return (c["x"] + c["w"] / 2, c["y"] + c["h"] / 2)

        def dist(a, b):
            return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5

        def overlap_pairs(rects):
            out = []
            for m in range(len(rects)):
                for k in range(m + 1, len(rects)):
                    a, b = rects[m], rects[k]
                    if a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"] and a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"]:
                        out.append(f"{a['id']}x{b['id']}")
            return out

        def start_rec(ms: int) -> None:
            pageA.evaluate(rec_js, {"identity": host["user"]["id"], "ms": ms})

        def analyze_rec(label: str, before_rects: list) -> dict:
            rec = pageA.evaluate("() => window.__lgRec")
            settled = cells(pageA)
            target = next((c for c in settled if c["id"] == host["user"]["id"]), None)
            samples = rec["samples"] if rec else []
            data = {"label": label, "samples": len(samples), "cells_before": len(before_rects), "cells_after": len(settled),
                    "final_rects": [[c["id"], c["x"], c["y"], c["w"], c["h"]] for c in settled], "overlap_pairs": overlap_pairs(settled)}
            if samples and target:
                first, last = samples[0], samples[-1]
                total = dist(center(first), center(last))
                steps = [dist(center(samples[m]), center(samples[m + 1])) for m in range(len(samples) - 1)]
                data.update({
                    "span_ms": samples[-1]["t"],
                    "moved_px": round(total, 2),
                    "max_step_px": round(max(steps), 2) if steps else None,
                    "max_step_ratio": round(max(steps) / total, 3) if steps and total > 1 else None,
                    "anim_durations_ms": rec["anims"],
                    "token_stage_move_ms": tokens.get("--stage-move-ms"),
                    "settle_delta_px": round(dist(center(last), center(target)), 2),
                })
            log(f"[E0/{label}]", json.dumps(data, ensure_ascii=False))
            return data

        # 场景 1：B 进场（布局 1 → 2 人重排）
        b_user = register(ctxB, "b", sfx)
        inv = ctxA.request.post(f"{API}/rooms/{room_id}/invites", data=json.dumps({"ttlSeconds": 60, "maxUses": 5}),
                                headers={"Content-Type": "application/json"})
        code = json.loads(inv.text())["data"]["code"] if inv.status == 201 else None
        if code:
            ctxB.request.post(f"{API}/invites/{code}/accept", data=json.dumps({}), headers={"Content-Type": "application/json"})
        pageB = ctxB.new_page()
        before1 = cells(pageA)
        start_rec(7000)
        stateB = enter(pageB, room_id)          # B 进房（开摄像头）→ A 端重排
        pageA.wait_for_timeout(2500)
        report["E0_join"] = analyze_rec("入场重排 1->2", before1)
        report["cells_after_join"] = len(cells(pageA))
        report["invite_code"] = code
        log(f"[B] 连接状态 = {stateB}")

        # 场景 2（焦点切换）并入下文「教学流程 3：举手 → 给焦点」——用 **UI 触发**才能带上广播，
        # 直接打 API 不会有 DataChannel 广播，A 端不会重排（本轮实测踩到，记在 changes.md）。

        # ---------- E11 声波证据 ----------
        wave = pageA.evaluate(
            """() => { const el = document.querySelector('.live-level'); if (!el) return null
                 const bars = Array.from(el.querySelectorAll('i'))
                 const cs = getComputedStyle(document.documentElement)
                 return { html: el.outerHTML.replace(/\\s+/g, ' '),
                          bars: bars.length, on: bars.filter((b) => b.classList.contains('on')).length,
                          bar_height: bars.length ? getComputedStyle(bars[0]).height : null,
                          pulses: [cs.getPropertyValue('--mic-pulse-ms').trim(), cs.getPropertyValue('--mic-pulse-min').trim()].join('/') } }"""
        )
        log("[E11] 声波控件:", json.dumps(wave, ensure_ascii=False))
        report["E11"] = wave
        shot(pageA, "mic-wave.png")

        steps: dict = {}
        # ---------- 教学流程 1：邀请（抽屉 → 邀请 tab → 生成） ----------
        try:
            opener = pageA.locator('[aria-label^="讨论与成员"]')
            if opener.count() and pageA.locator('button:has-text("邀请")').count() == 0:
                opener.first.click()
                pageA.wait_for_timeout(400)
            pageA.locator('button:has-text("邀请")').first.click()
            pageA.wait_for_timeout(300)
            pageA.locator('button:has-text("生成邀请码")').first.click()
            pageA.wait_for_timeout(1200)
            panel = pageA.locator('section:has-text("邀请链接（限时）")').first.inner_text()
            steps["invite_ui"] = panel.replace("\n", " | ")[:200]
            log("[教学] 邀请面板 UI 文案:", steps["invite_ui"])
            shot(pageA, "invite-panel.png")
        except Exception as exc:  # noqa: BLE001
            steps["invite_ui"] = f"失败: {exc}"
            log("[教学] 邀请 UI 失败:", exc)

        # ---------- 教学流程 2：凭码加入页 ----------
        try:
            pageC = ctxC.new_page()
            pageC.goto(f"{WEB}/join?code={code}", wait_until="domcontentloaded")
            pageC.wait_for_timeout(1200)
            steps["join_prefill"] = pageC.evaluate("() => { const i = document.querySelector('input'); return i ? i.value : 'no-input' }")
            shot(pageC, "join-page.png")
            pageC.locator('button:has-text("加入房间")').first.click()
            pageC.wait_for_url(f"**/rooms/{room_id}/live", timeout=15000)
            steps["join_landed"] = pageC.url
            log("[教学] 凭码加入 → 落到", pageC.url)
        except Exception as exc:  # noqa: BLE001
            steps["join_landed"] = f"失败: {exc}"
            log("[教学] 凭码加入失败:", exc)

        # ---------- 教学流程 3：举手 → 房主「给焦点」 ----------
        try:
            pageB.locator('button:has-text("举手")').first.click()
            pageA.wait_for_selector(".live-cell.is-hand", timeout=15000)
            hand_ids = pageA.evaluate("() => Array.from(document.querySelectorAll('.live-cell.is-hand')).map((e) => e.dataset.flipId)")
            steps["hand_seen"] = hand_ids
            before_focus = cells(pageA)
            start_rec(5000)
            pageA.locator(".live-cell.is-hand button:has-text(\"给焦点\")").first.click()
            pageA.wait_for_timeout(4500)
            focus_a = [c["id"] for c in cells(pageA) if c["focus"]]
            focus_b = [c["id"] for c in cells(pageB) if c["focus"]]
            hand_left = pageA.evaluate("() => document.querySelectorAll('.live-cell.is-hand').length")
            b_label = pageB.evaluate("() => Array.from(document.querySelectorAll('.live-ctrl-text')).map((e) => e.textContent)")
            steps["focus_after_grant"] = {"A": focus_a, "B": focus_b, "hand_left": hand_left, "B_button": b_label}
            report["E0_third_join"] = analyze_rec("第三人加入重排 2->3（含举手→给焦点期间）", before_focus)
            log("[教学] 举手→给焦点:", json.dumps(steps["focus_after_grant"], ensure_ascii=False))
            # 观测（不归因）：执行「给焦点」的一方（房主 A）界面是否把焦点算进布局
            steps["focus_sync_observation"] = pageA.evaluate(
                """() => ({ a_stage_mode: document.querySelector('[data-stage-mode]')?.dataset.stageMode,
                            a_is_focus_cells: document.querySelectorAll('.live-cell.is-focus').length,
                            a_stage_ids: document.querySelector('[data-stage-ids]')?.dataset.stageIds })"""
            )
            log("[观测] A 端布局:", json.dumps(steps["focus_sync_observation"], ensure_ascii=False))
            shot(pageA, "focus-granted.png")
        except Exception as exc:  # noqa: BLE001
            steps["focus_after_grant"] = f"失败: {exc}"
            log("[教学] 焦点流程失败:", exc)
        report["steps"] = steps
        log("[mid] 阶段小结:", json.dumps(report, ensure_ascii=False)[:1200])

        # ---------- 教学流程 4：结束房间 → 列表「讨论纪要」→ 生成 ----------
        try:
            pageA.locator('button:has-text("结束房间")').first.click()
            pageA.wait_for_timeout(400)
            pageA.locator('[role="dialog"] button:has-text("结束房间")').first.click()
            pageA.wait_for_timeout(2500)
            steps["after_end_url"] = pageA.url
            pageA.goto(WEB + "/", wait_until="domcontentloaded")
            pageA.wait_for_timeout(1500)
            ended = pageA.locator('button:has-text("已结束")').first
            if ended.count():
                ended.click()
                pageA.wait_for_timeout(800)
            card_btn = pageA.locator('button:has-text("讨论纪要")').first
            steps["list_entry_visible"] = card_btn.count() > 0
            if card_btn.count():
                card_btn.click()
                pageA.wait_for_url(f"**/rooms/{room_id}/summary", timeout=15000)
            else:
                pageA.goto(f"{WEB}/rooms/{room_id}/summary", wait_until="domcontentloaded")
            pageA.wait_for_timeout(1000)
            steps["summary_page"] = pageA.url
            gen = pageA.locator('button:has-text("生成讨论纪要")').first
            if gen.count():
                t_gen0 = time.time()
                gen.click()
                for _ in range(60):
                    pageA.wait_for_timeout(1000)
                    txt = pageA.inner_text("body")
                    if "主题与背景" in txt or "讨论要点" in txt:
                        break
                steps["summary_seconds"] = round(time.time() - t_gen0, 1)
            body = pageA.inner_text("body")
            steps["summary_ok"] = ("主题与背景" in body) or ("讨论要点" in body)
            steps["summary_chars"] = len(body)
            log("[教学] 纪要页:", steps["summary_ok"], "正文长度", steps["summary_chars"])
            shot(pageA, "summary-page.png")
        except Exception as exc:  # noqa: BLE001
            steps["summary_ok"] = f"失败: {exc}"
            log("[教学] 纪要流程失败:", exc)

        # ---------- 结论 ----------
        report["shots"] = SHOTS
        report["console_tail"] = console[-6:]
        log("\n===== REPORT =====")
        log(json.dumps(report, ensure_ascii=False, indent=1))
        out_json = os.path.join(OUT, f"report-{sfx}.json")
        with io_open(out_json, "w") as fh:
            fh.write(json.dumps(report, ensure_ascii=False, indent=1))
        log("报告落盘:", out_json)
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
