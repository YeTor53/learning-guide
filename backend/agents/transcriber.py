"""r010 转写 worker（A 路径识别侧；ADR-0023）。

做什么：被派单进房 → 订阅音频（AUDIO_ONLY）→ 给**有音频轨的**参与者各开一个 `AgentSession` →
识别结果由官方通道注入房间（前端 `RoomEvent.TranscriptionReceived` 收，带 participant 身份）。

设计事实源：`docs/rounds/r010-transcription/design.md` §9.1/§9.2；实测依据：`spike-01-path-a.md`。
运行（独立环境 `lg_agents`，**不装进后端主环境**）：
    conda activate lg_agents
    python backend/agents/transcriber.py dev          # 需要 .env 里的 LIVEKIT_*

环境变量：
    AGENT_NAME          默认 learning-guide-transcriber（须与后端 STT_AGENT_NAME 一致）
    AGENT_STT           inference（默认，走 LiveKit Inference，免费档）/ fake（离线假 STT，零配额，供 E2E 与自测）
    AGENT_STT_MODEL     默认 deepgram/nova-3
    AGENT_LANGUAGE      默认 zh
    AGENT_MAX_SESSIONS  默认 5（免费档 Inference STT 并发上限；超限只告警跳过）

纪律：不认识别的人、不回话、不调 LLM；只转写；关麦 = 无音频 = 自然不转写。
"""
from __future__ import annotations

import asyncio
import logging
import os

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    AutoSubscribe,
    JobContext,
    StopResponse,
    cli,
    inference,
    room_io,
)
from livekit.agents import stt as stt_mod
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, NOT_GIVEN
from livekit import rtc

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("transcriber")

AGENT_NAME = os.environ.get("AGENT_NAME", "learning-guide-transcriber")
STT_MODE = os.environ.get("AGENT_STT", "inference")           # inference | fake
STT_MODEL = os.environ.get("AGENT_STT_MODEL", "deepgram/nova-3")
LANGUAGE = os.environ.get("AGENT_LANGUAGE", "zh")
MAX_SESSIONS = int(os.environ.get("AGENT_MAX_SESSIONS", "5"))
FAKE_INTERVAL = float(os.environ.get("AGENT_FAKE_INTERVAL", "3.0"))


def _is_audio_track(obj) -> bool:
    """音频轨判定：兼容 `Track` 与 `TrackPublication`（两者都有 `kind`）。"""
    kind = getattr(obj, "kind", None)
    return kind == rtc.TrackKind.KIND_AUDIO or str(kind).endswith("KIND_AUDIO")


class _FakeStream(stt_mod.RecognizeStream):
    """离线假 STT 的流：每 FAKE_INTERVAL 秒吐一条最终稿（内容带序号，便于端到端断言）。零配额。"""

    def __init__(self, owner: "FakeSTT", *, conn_options) -> None:
        super().__init__(stt=owner, conn_options=conn_options)
        self._owner = owner
        self._n = 0

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(FAKE_INTERVAL)
            self._n += 1
            self._event_ch.send_nowait(
                stt_mod.SpeechEvent(
                    type=stt_mod.SpeechEventType.FINAL_TRANSCRIPT,
                    alternatives=[stt_mod.SpeechData(language=LANGUAGE, text=f"【离线桩】第 {self._n} 条")],
                )
            )


class FakeSTT(stt_mod.STT):
    """离线假 STT（`AGENT_STT=fake`）：不打任何外部服务，用于零配额的真机联调与演示降级。"""

    def __init__(self) -> None:
        super().__init__(
            capabilities=stt_mod.STTCapabilities(streaming=True, interim_results=False, diarization=False)
        )

    @property
    def model(self) -> str:
        return "fake-stt"

    @property
    def provider(self) -> str:
        return "offline-stub"

    async def _recognize_impl(self, buffer, *, language=NOT_GIVEN, conn_options=DEFAULT_API_CONNECT_OPTIONS):
        return stt_mod.SpeechEvent(
            type=stt_mod.SpeechEventType.FINAL_TRANSCRIPT,
            alternatives=[stt_mod.SpeechData(language=LANGUAGE, text="【离线桩】单段")],
        )

    def stream(self, *, language=NOT_GIVEN, conn_options=DEFAULT_API_CONNECT_OPTIONS):
        return _FakeStream(self, conn_options=conn_options)


def _build_stt():
    """识别器工厂：默认走 LiveKit Inference（免费档，无需自备 key），测试可切离线桩。"""
    if STT_MODE == "fake":
        logger.warning("AGENT_STT=fake：使用离线假 STT（零配额，仅供联调/演示降级）")
        return FakeSTT()
    return inference.STT(STT_MODEL, language=LANGUAGE)


class Transcriber(Agent):
    """只转写、不回话的 agent。"""

    def __init__(self, *, participant_identity: str) -> None:
        super().__init__(instructions="not-needed", stt=_build_stt())
        self.participant_identity = participant_identity

    async def on_user_turn_completed(self, turn_ctx, new_message) -> None:
        logger.info("转写 %s：%s", self.participant_identity, (new_message.text_content or "")[:80])
        raise StopResponse()   # 不触发 LLM/回复


class TranscriberPool:
    """每个**有音频轨的**参与者一个会话；超过 MAX_SESSIONS 只告警跳过（免费档并发护栏）。"""

    def __init__(self, ctx: JobContext) -> None:
        self.ctx = ctx
        self._sessions: dict[str, AgentSession] = {}
        self._pending: set[str] = set()
        self._tasks: set[asyncio.Task] = set()

    def start(self) -> None:
        self.ctx.room.on("participant_connected", self._on_participant_connected)
        self.ctx.room.on("participant_disconnected", self._on_participant_disconnected)
        self.ctx.room.on("track_subscribed", self._on_track_subscribed)

    async def aclose(self) -> None:
        for pid in list(self._sessions):
            await self._close_session(pid)
        for task in list(self._tasks):
            task.cancel()

    # ---- 事件 ----

    def _on_participant_connected(self, participant) -> None:
        self._maybe_start(participant)

    def _on_track_subscribed(self, track, publication, participant) -> None:
        # 先连人后开麦的情况：音频轨订阅成功后再补开会话
        if _is_audio_track(track):
            self._maybe_start(participant)

    def _on_participant_disconnected(self, participant) -> None:
        task = asyncio.create_task(self._close_session(participant.identity))
        self._tasks.add(task)
        task.add_done_callback(lambda t: self._tasks.discard(t))

    # ---- 内部 ----

    @staticmethod
    def _has_audio(participant) -> bool:
        """参与者是否已发布音频轨（没麦的人不开会话，省并发也省额度）。"""
        return any(_is_audio_track(pub) for pub in (getattr(participant, "track_publications", {}) or {}).values())

    def _maybe_start(self, participant) -> None:
        pid = participant.identity
        if pid in self._sessions or pid in self._pending:
            return
        if pid.startswith("agent-") or not self._has_audio(participant):
            return
        if len(self._sessions) + len(self._pending) >= MAX_SESSIONS:
            logger.warning("已达 MAX_SESSIONS=%d，跳过 %s（免费档并发护栏）", MAX_SESSIONS, pid)
            return
        self._pending.add(pid)
        task = asyncio.create_task(self._start_session(participant))
        self._tasks.add(task)

        def _done(t: asyncio.Task) -> None:
            self._tasks.discard(t)
            self._pending.discard(pid)
            try:
                self._sessions[pid] = t.result()
            except Exception:  # noqa: BLE001
                logger.exception("开转写会话失败：%s", pid)

        task.add_done_callback(_done)

    async def _start_session(self, participant) -> AgentSession:
        logger.info("开转写会话：%s", participant.identity)
        session = AgentSession()
        await session.start(
            agent=Transcriber(participant_identity=participant.identity),
            room=self.ctx.room,
            room_options=room_io.RoomOptions(
                audio_input=True,
                text_output=True,      # 转写经官方通道注入房间（前端 TranscriptionReceived 收）
                audio_output=False,
                text_input=False,
                participant_identity=participant.identity,
            ),
        )
        return session

    async def _close_session(self, pid: str) -> None:
        session = self._sessions.pop(pid, None)
        if session is None:
            return
        logger.info("关转写会话：%s", pid)
        try:
            await session.drain()
            await session.aclose()
        except Exception:  # noqa: BLE001
            logger.exception("关会话失败：%s", pid)


server = AgentServer()


@server.rtc_session(agent_name=AGENT_NAME)
async def entrypoint(ctx: JobContext) -> None:
    logger.info("被派单进房：room=%s agent=%s stt=%s max=%d", ctx.room.name, AGENT_NAME, STT_MODE, MAX_SESSIONS)
    pool = TranscriberPool(ctx)
    pool.start()
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    for participant in ctx.room.remote_participants.values():
        pool._maybe_start(participant)
    ctx.add_shutdown_callback(pool.aclose)


if __name__ == "__main__":
    cli.run_app(server)
