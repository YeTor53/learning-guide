"""r010 转写真机回归脚本（零配额档：worker 用 AGENT_STT=fake 也能跑）。

验什么（三层，逐层给数字）：
  1) **音频路径是真的**：给 Chromium 喂一段 TTS 语音当麦克风（`--use-file-for-fake-audio-capture`），
     在**本端**用 WebAudio 量自己采集的 RMS（证明确有语音在采集），在**对端**量收到的远端音频 RMS
     （证明音频真的经 LiveKit 传到了别人那里）。
  2) **转写链路**：worker 是否给每个有音频轨的参与者开会话（worker 日志）、前端是否出转写气泡、
     `/conversation` 是否查得到、气泡是否带说话人。
  3) **一致性与幂等**：多端都能看到别人的话；库内唯一行数由 `--room-db-check` 另行核对（见报告 §库内取证）。

设计事实源：`docs/rounds/r010-transcription/design.md` §9；实测结论见 `review.md` §3.5。
用法（前置：`dev.bat` 已起 8000+5173；`agents.bat`（可 `set AGENT_STT=fake`）已起）：
    python frontend/scripts/verify-transcription.py --wav-a "%TEMP%\\lg_r010_audio\\line_a.wav" ^
        --wav-b "%TEMP%\\lg_r010_audio\\line_b.wav" --worker-log "%TEMP%\\lg_r010_e2e\\worker.log"
"""
from __future__ import annotations

import argparse
import asyncio
import io
import json
import os
import re
import sys
import time

from playwright.async_api import async_playwright

PW = "demo-pass-123"
RMS_SAMPLE_JS = """
async () => {
  const ctx = new (window.AudioContext || window.webkitAudioContext)();
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const src = ctx.createMediaStreamSource(stream);
  const an = ctx.createAnalyser();
  an.fftSize = 2048;
  src.connect(an);
  const buf = new Float32Array(an.fftSize);
  const out = [];
  const t0 = performance.now();
  while (performance.now() - t0 < window.__rmsMs) {
    an.getFloatTimeDomainData(buf);
    let sum = 0;
    for (let i = 0; i < buf.length; i++) sum += buf[i] * buf[i];
    out.push(Math.sqrt(sum / buf.length));
    await new Promise((r) => setTimeout(r, 200));
  }
  stream.getTracks().forEach((t) => t.stop());
  await ctx.close();
  return out;
}
"""
# 对端收到的远端音频：读 WebRTC 接收统计（不依赖本机音频输出设备，有无扬声器都成立）。
# 依据：r004 留的 dev 调试句柄 window.__lgRoom（仅 DEV 构建）。
INBOUND_STATS_JS = """
async () => {
  const room = window.__lgRoom;
  if (!room) return { error: 'no-dev-handle' };
  const pubs = [...room.remoteParticipants.values()].flatMap((p) =>
    [...p.trackPublications.values()]
      .filter((pub) => pub.kind === 'audio' && pub.track)
      .map((pub) => ({ pub, who: p.identity })));
  const rows = [];
  for (const { pub, who } of pubs) {
    let inb = null;
    try {
      const report = await pub.track.getRTCStatsReport();
      report.forEach((s) => { if (s.type === 'inbound-rtp' && (s.kind === 'audio' || s.mediaType === 'audio')) inb = s; });
    } catch (e) { /* 统计不可得时留 null */ }
    rows.push({
      identity: who,
      bytes: inb ? inb.bytesReceived : null,
      packets: inb ? inb.packetsReceived : null,
      energy: inb ? (inb.totalAudioEnergy ?? null) : null,
      level: inb ? (inb.audioLevel ?? null) : null,
    });
  }
  return { count: pubs.length, rows };
}
"""


def stats(samples: list[float] | None) -> dict:
    if not samples:
        return {"n": 0, "peak": None, "mean": None}
    return {"n": len(samples), "peak": round(max(samples), 5), "mean": round(sum(samples) / len(samples), 5)}


CONNECTED_JS = """
() => {
  const room = window.__lgRoom;
  if (!room) return { handle: false };
  return { handle: true, state: room.state, remotes: room.remoteParticipants.size };
}
"""


async def wait_connected(page, *, expect_remotes: int, timeout: float = 45.0, tag: str = "") -> dict:
    """等页面真的连上 LiveKit（本机首连常先超时再换区，实测约 10 秒）——不等就会误判「没有远端音频」。"""
    import time as _t

    t0 = _t.time()
    last: dict = {}
    while _t.time() - t0 < timeout:
        last = await page.evaluate(CONNECTED_JS)
        if last.get("state") == "connected" and (last.get("remotes") or 0) >= expect_remotes:
            return {**last, "waited": round(_t.time() - t0, 1), "tag": tag}
        await asyncio.sleep(1)
    return {**last, "waited": round(_t.time() - t0, 1), "tag": tag, "timeout": True}


async def api(ctx, method: str, path: str, **kw):
    resp = await getattr(ctx.request, method)(f"{BASE}/api{path}", **kw)
    try:
        body = await resp.json()
    except Exception:  # noqa: BLE001
        body = None
    return resp.status, body


async def register(ctx, name: str) -> dict:
    st, body = await api(ctx, "post", "/auth/register", data={"email": f"vt_{int(time.time())}_{os.getpid()}@example.com", "displayName": name, "password": PW})
    return {"status": st, "userId": ((body or {}).get("data") or {}).get("user", {}).get("id")}


async def join_and_open(browser, room_id: str, name: str, wav: str | None):
    ctx = await browser.new_context(permissions=["microphone"], viewport={"width": 1440, "height": 900})
    who = await register(ctx, name)
    st, body = await api(ctx, "post", f"/rooms/{room_id}/join-requests", data={"message": ""})
    request_id = ((body or {}).get("data") or {}).get("id")
    page = await ctx.new_page()
    page_errors: list[str] = []
    page.on("pageerror", lambda e: page_errors.append(str(e)[:160]))
    await page.goto(f"{BASE}/rooms/{room_id}/live", wait_until="domcontentloaded")
    return {"ctx": ctx, "page": page, "who": who, "requestId": request_id, "errors": page_errors}


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:5173")
    ap.add_argument("--wav-a", required=True)
    ap.add_argument("--wav-b", required=True)
    ap.add_argument("--worker-log", default=None, help="worker 日志路径（用于核对是否为每个参与者开了会话）")
    ap.add_argument("--sample-ms", type=int, default=8000)
    ap.add_argument("--settle", type=int, default=35, help="等 agent 入场 + 累积转写的秒数")
    ap.add_argument("--json", default=os.path.join(os.environ.get("TEMP", "."), "lg_r010_verify.json"))
    global BASE
    args = ap.parse_args()
    BASE = args.base_url.rstrip("/")
    rep: dict = {"baseUrl": BASE, "wavA": os.path.basename(args.wav_a), "wavB": os.path.basename(args.wav_b), "steps": {}, "audio": {}, "transcribe": {}, "fail": []}

    for path in (args.wav_a, args.wav_b):
        if not os.path.isfile(path):
            print(f"[FAIL] 语音素材不存在：{path}")
            return 2

    async with async_playwright() as p:
        common = ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream",
                  "--autoplay-policy=no-user-gesture-required", "--mute-audio"]
        # 两个发布者各自一个浏览器实例（`--use-file-for-fake-audio-capture` 是**进程级**参数）
        br_a = await p.chromium.launch(args=[*common, f"--use-file-for-fake-audio-capture={args.wav_a}"])
        br_b = await p.chromium.launch(args=[*common, f"--use-file-for-fake-audio-capture={args.wav_b}"])
        br_w = await p.chromium.launch(args=common)

        host_ctx = await br_w.new_context(permissions=["microphone"])
        rep["steps"]["register_host"] = await register(host_ctx, "房主VT")
        st, body = await api(host_ctx, "post", "/rooms", data={"topic": "custom", "topicLabel": "转写", "title": "转写回归房", "description": ""})
        room_id = ((body or {}).get("data") or {}).get("id")
        rep["steps"]["create_room"] = {"status": st, "roomId": room_id}
        if not room_id:
            print("[FAIL] 建房失败", body)
            return 2

        a = await join_and_open(br_a, room_id, "甲VT", args.wav_a)
        b = await join_and_open(br_b, room_id, "乙VT", args.wav_b)
        w = await join_and_open(br_w, room_id, "观察VT", None)
        for who in (a, b, w):
            st2, _ = await api(host_ctx, "post", f"/join-requests/{who['requestId']}/approve")
            rep["steps"].setdefault("approve", []).append(st2)
        host_page = await host_ctx.new_page()
        await host_page.goto(f"{BASE}/rooms/{room_id}/live", wait_until="domcontentloaded")
        await asyncio.sleep(4)

        # ---- 0) 等每个页面真的连上（远端人数 = 其余 3 人）----
        rep["steps"]["connected"] = {}
        for name, item in (("房主VT", {"page": host_page}), ("甲VT", a), ("乙VT", b), ("观察VT", w)):
            rep["steps"]["connected"][name] = await wait_connected(item["page"], expect_remotes=3, tag=name)

        # ---- 1) 音频路径 ----
        for tag, item in (("甲VT", a), ("乙VT", b)):
            await item["page"].evaluate(f"window.__rmsMs = {args.sample_ms}")
            samples = await item["page"].evaluate(RMS_SAMPLE_JS)
            rep["audio"][f"own_{tag}"] = stats(samples)
        # 对端收音频：取两次统计量，算增量（音频真在流 → bytes/energy 增长）
        s1 = await w["page"].evaluate(INBOUND_STATS_JS)
        await asyncio.sleep(4)
        s2 = await w["page"].evaluate(INBOUND_STATS_JS)
        rows2 = {r["identity"]: r for r in (s2 or {}).get("rows", [])}
        flows = []
        for r1 in (s1 or {}).get("rows", []):
            r2 = rows2.get(r1["identity"], {})
            flows.append({
                "identity": r1["identity"],
                "dBytes": (r2.get("bytes") or 0) - (r1.get("bytes") or 0),
                "dEnergy": (r2.get("energy") or 0) - (r1.get("energy") or 0),
                "audioLevel": r2.get("level"),
            })
        rep["audio"]["inbound_观察VT"] = {"tracks": (s2 or {}).get("count"), "flows": flows,
                                         "devHandle": not (s1 or {}).get("error")}

        # ---- 2) 等 agent 入场与转写累积 ----
        agent_seen = None
        t0 = time.time()
        while time.time() - t0 < args.settle:
            await asyncio.sleep(2)
            chips = await host_page.evaluate("() => (document.querySelector('.live-transcribe-chip')||{}).textContent||''")
            if "开启" in chips:
                agent_seen = round(time.time() - t0, 1)
                break
        rep["steps"]["agent_seen_after_seconds"] = agent_seen
        await asyncio.sleep(max(0, args.settle - (time.time() - t0)))

        # ---- 3) 转写链路 ----
        for tag, item in (("host", {"page": host_page, "ctx": host_ctx}), ("甲VT", a), ("乙VT", b), ("观察VT", w)):
            page = item["page"]
            try:
                await page.locator(".live-drawer-toggle").first.click(timeout=4000)
                await asyncio.sleep(1.0)
            except Exception:  # noqa: BLE001
                pass
            dom = await page.evaluate("""() => ({
                speech: document.querySelectorAll('.chat-bubble-speech').length,
                live: document.querySelectorAll('.chat-bubble-speech-live').length,
                chip: (document.querySelector('.live-transcribe-chip')||{}).textContent||null,
                speakers: [...new Set([...document.querySelectorAll('.chat-bubble-speech .chat-who')].map((e) => e.textContent.trim()))],
            })""")
            st3, body3 = await api(item["ctx"], "get", f"/rooms/{room_id}/conversation")
            items = ((body3 or {}).get("data") or {}).get("items") or []
            speech = [i for i in items if i.get("kind") == "speech"]
            rep["transcribe"][tag] = {"dom": dom, "conversation": {"status": st3, "total": len(items), "speech": len(speech),
                                                                 "speakers": sorted({i.get("speakerName") for i in speech})}}

        # ---- worker 日志核对 ----
        if args.worker_log and os.path.isfile(args.worker_log):
            log = io.open(args.worker_log, encoding="utf-8", errors="replace").read()
            sessions = re.findall(r"开转写会话：(\S+)", log)
            rep["worker"] = {"sessions_total": len(sessions), "distinct": sorted(set(sessions)),
                             "for_this_room": len(re.findall(re.escape(room_id), log))}
        await br_a.close(), await br_b.close(), await br_w.close()

    # ---- 断言 ----
    own_a = rep["audio"].get("own_甲VT", {}).get("peak") or 0
    own_b = rep["audio"].get("own_乙VT", {}).get("peak") or 0
    inb_info = rep["audio"].get("inbound_观察VT", {})
    inb_tracks = inb_info.get("tracks") or 0
    inb_bytes = max([f.get("dBytes") or 0 for f in inb_info.get("flows", [])] or [0])
    inb_energy = max([f.get("dEnergy") or 0 for f in inb_info.get("flows", [])] or [0])
    if own_a < 0.01:
        rep["fail"].append(f"甲VT 本端采集 RMS 峰值过低（{own_a}）→ TTS 语音没进麦克风")
    if own_b < 0.01:
        rep["fail"].append(f"乙VT 本端采集 RMS 峰值过低（{own_b}）→ TTS 语音没进麦克风")
    if inb_tracks < 1:
        rep["fail"].append("观察端没有订阅到任何远端音频轨 → 音频没到对端")
    elif inb_bytes < 5000:
        rep["fail"].append(f"观察端 4 秒内收到的音频字节增量过小（{inb_bytes}）→ 音频没在流")
    elif inb_energy <= 0:
        rep["fail"].append("观察端 totalAudioEnergy 无增长 → 收到的是静音（音频内容没到）")
    if rep["steps"].get("agent_seen_after_seconds") is None:
        rep["fail"].append("控制坞始终未显示「转写：开启」→ worker 未入场")
    host_conv = rep["transcribe"].get("host", {}).get("conversation", {})
    if (host_conv.get("speech") or 0) < 2:
        rep["fail"].append(f"房主端 /conversation 的 speech 条数不足（{host_conv.get('speech')}）→ 转写未落库")
    if (rep["transcribe"].get("host", {}).get("dom", {}).get("speech") or 0) < 1:
        rep["fail"].append("房主端界面没有转写气泡")

    io.open(args.json, "w", encoding="utf-8").write(json.dumps(rep, ensure_ascii=False, indent=1))
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    print("\n结论:", "PASS" if not rep["fail"] else "FAIL → " + "; ".join(rep["fail"]))
    print("报告:", args.json)
    return 0 if not rep["fail"] else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
