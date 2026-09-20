---
title: r010 函数级设计：语音转文字并入讨论流（路径 B + 官方协议）
description: 逐文件的函数签名与职责——STT 唯一出口、转写落库、三源合一对话流、前端默认开启与分段上传。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-20
---

<!-- overview -->
需求 `docs/00-requirements/r010-transcription.md`；调研 `research-01/02.md`；决定 ADR-0022。
状态：**draft（等你读完再批）** —— 你 2026-09-20 表态「设计我都没看，看完回复」，故此页状态从 `approved` 退回 `draft`。
**如实标注**：cp-1 的后端代码（迁移 + STT 出口 + 路由 + 用例）已按本页落地并跑绿，属「设计未获明确批准先实现」；你读完批了即追认，若要改，改动清单先出、前端尚未动。
实现期的依赖登记见 `cr-01.md`（L3，已按建议值执行）。界面口径七项见需求单，本页 §3.2 是视觉契约（令牌 / 动效 / 文案）。

## 1. 数据层

### 1.1 迁移 `backend/app/db/sql/009_r010_transcripts.sql`

```sql
CREATE TABLE IF NOT EXISTS transcripts (
  id            TEXT PRIMARY KEY,                       -- 段稳定标识（= 官方 TranscriptionSegment.id 的口径）
  room_id       TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
  speaker_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  segment_index INTEGER NOT NULL CHECK (segment_index >= 0),  -- 本端分段序号（去重/排序）
  text          TEXT NOT NULL CHECK (length(text) > 0),
  language      TEXT NOT NULL DEFAULT 'zh',
  started_at    TIMESTAMPTZ NOT NULL,                   -- 该段音频开始（客户端时钟换算 UTC）
  duration_ms   INTEGER NOT NULL CHECK (duration_ms > 0),
  final         BOOLEAN NOT NULL DEFAULT TRUE,          -- 本轮只落最终稿；保留字段对齐官方契约
  provider      TEXT NOT NULL DEFAULT '',               -- 供应商标识（便于换服务后追溯）
  model         TEXT NOT NULL DEFAULT '',
  created_at    TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_transcripts_segment ON transcripts (room_id, speaker_id, segment_index);
CREATE INDEX IF NOT EXISTS ix_transcripts_room_time ON transcripts (room_id, started_at);
```

## 2. 后端

### 2.1 `app/config.py`（新增）
```python
stt_base_url: str = ""          # STT_BASE_URL（Whisper 兼容；空 = 未配置）
stt_api_key: str = ""           # STT_API_KEY（空 = 未配置）
stt_model: str = "whisper-1"    # STT_MODEL
stt_segment_seconds: int = 8    # 前端建议分段（接口回给前端，改一处即生效）
stt_max_seconds: int = 30       # 单段上限
stt_max_bytes: int = 10 * 1024 * 1024
```

### 2.2 `app/repositories/transcripts.py`（新增）
```python
@dataclass(frozen=True) class NewTranscript: id, room_id, speaker_id, segment_index, text, language, started_at, duration_ms, provider, model
@dataclass(frozen=True) class TranscriptRow(NewTranscript): created_at

def insert_transcript(conn, row: NewTranscript) -> bool            # ON CONFLICT (room,speaker,index) DO NOTHING；False=重复
def list_transcripts(conn, room_id, *, limit=200) -> list[TranscriptRowWithName]   # 按 started_at ASC
def count_speakers(conn, room_id) -> int
```

### 2.3 `app/services/stt.py`（新增；**唯一 STT 出口**）

> 依赖：后端→STT 的 multipart 由 `aiohttp.FormData` 发（`aiohttp` 已有）；**前端→后端的 multipart 解析需要 `python-multipart`**（FastAPI 官方要求），见 `cr-01.md`（2026-09-20 追加进 `backend/requirements.txt`）。
```python
class SttNotConfigured(Exception)  # → 503 STT_NOT_CONFIGURED
class SttError(Exception)          # → 502 STT_FAILED

def stt_available() -> tuple[bool, str]      # (是否配置, 模型名)
async def call_stt(audio: bytes, *, filename: str, language: str | None = None, client=None) -> SttResult
    """Whisper 兼容：multipart POST {base}/audio/transcriptions（model/file/language）。
       client 可注入 → 用例全离线打桩。返回 {text, language, provider, model}。"""
def estimate_segment_seconds() -> int        # 回给前端的建议分段
```
纪律：与 `call_llm`（r008）同级——**外部调用唯一出口、失败不改业务真相、可注入打桩、不打印文本内容**。

### 2.4 `app/services/transcripts.py`（新增）
```python
def transcribe_segment(conn, actor: UserVO, room_id: str, *, audio: bytes, filename: str,
                       segment_index: int, started_at: datetime, duration_ms: int,
                       language: str | None = None) -> TranscriptVO
    """权限=在册成员；房间 active；限长限大；调 call_stt；`insert_transcript` 去重；
       未配置 → SttNotConfigured（不落库）；STT 失败 → SttError（不落库，客户端重试一次即可）。"""

def list_transcripts(conn, actor: UserVO, room_id: str, *, limit: int = 200) -> list[TranscriptVO]
    """本房成员（含已离开）与房主/协管可读；房间可 ended（只读）。"""

@dataclass(frozen=True) class ConversationItem:
    id: str; kind: str            # 'chat' | 'system' | 'speech'
    at: datetime; speaker_id: str | None; speaker_name: str | None
    text: str; meta: dict[str, Any]   # speech: {durationMs}; system: {event}

def build_conversation(conn, actor: UserVO, room_id: str, *, limit: int = 200) -> list[ConversationItem]
    """三源合一（R2/R3）：chat_messages(kind='chat') + chat_messages(kind='system') + transcripts，
       统一键 at（转写用 started_at）、按 at ASC + id 稳定排序，截最近 limit 条。"""
```

### 2.5 `app/api/routers/transcripts.py`（新增）
| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/rooms/{room_id}/transcripts` | multipart：`file`(音频) + `segmentIndex` + `startedAt` + `durationMs` + 可选 `language` → 201 `{transcript}`；503/502/400/409 |
| GET | `/api/rooms/{room_id}/transcripts?limit=` | 200 `{transcripts}` |
| GET | `/api/rooms/{room_id}/conversation?limit=` | 200 `{items}`（三源合一） |
| GET | `/api/stt/status` | 200 `{configured, model, segmentSeconds, maxSeconds, maxBytes}` |

新增错误码：`STT_FAILED`(502)。沿用：`STT_NOT_CONFIGURED`(503)、`ROOM_ENDED`(409)、`VALIDATION`(400)。

## 3. 前端

| 文件 | 职责 / 签名 |
| --- | --- |
| `api/transcripts.ts` | `transcriptsApi.upload(roomId, {blob, segmentIndex, startedAt, durationMs})`、`.list`、`.conversation`、`.sttStatus` |
| `hooks/useTranscription.ts` | `useTranscription(room, roomId, enabled, identity)` → `{on, toggle, notice, error, state}`：**默认开启**（localStorage 记忆「本人关闭过」）、`MediaRecorder` **8 秒**一段、能量门限跳静音段、失败重试 1 次、关闭瞬间 `stop()` 并丢弃在途段 |
| `components/live/TranscribeNotice.tsx` | 进房一次性告知条：「本房间会把你说的内容转成文字，供大家与纪要使用」+「关闭转写」+「知道了」（30 秒后本端可关掉，不挡操作） |
| `components/live/ConversationPanel.tsx` | 三源合一渲染：`kind='chat'` 气泡 / `kind='system'` 细行 / **`kind='speech'` 气泡**（麦克风小图标 + 说话人 + 时间 + 时长） |
| `components/live/RoomSidePanel.tsx` | 「讨论」tab 改用 `ConversationPanel`（原 `ChatPanel` 的消息区复用，新增 speech 样式） |

样式令牌（`global.css`）：`--speech-bar-color`、`--speech-icon-size`、`--transcribe-notice-ms`（告知条自动收起），可单点调；明细见 §3.2。

### 3.2 视觉契约（契约类；**未批不动样式代码**）

**令牌表**（唯一取值来源）：本轮**只新增 3 个**，写在 `frontend/src/styles/global.css` 的**新 `:root` 段**（段头注释与 r004/r009 同风格：写「设计事实源 + 调参入口全在这一段」）。

| 令牌 | 值 | 作用 | 可调范围 |
| --- | --- | --- | --- |
| `--speech-bar-color` | `rgba(124, 240, 196, 0.45)` | 转写气泡**左侧 3px 色条**（与举手/焦点同色系；这是与聊天气泡的唯一视觉区分） | 任意色值 |
| `--speech-icon-size` | `14px` | 气泡内麦克风图标（lucide `Mic`）尺寸 | 12~18px |
| `--transcribe-notice-ms` | `30000`（**无单位**，JS 读，口径同 `--stage-move-ms`） | 告知条自动收起的毫秒数；`0` = 不自动收 | 0~120000 |

**复用既有令牌，不新增**（改动只落在这 3 个新令牌 + 一个气泡变体类）：`.chat-bubble` 壳（`--panel-strong` 底 / `--line-soft` 边 / 12px 圆角）、`--chat-body-size`(13px)、`--chat-bubble-max`(420px)、入场动画 `@keyframes chat-enter` + `--msg-enter`(120ms) + `--ease`。

**动效清单**（每处一行；「参数写在哪」都是 `global.css` 的 `:root` 段这一处）：

| 位置 | 触发 | 位移/时长/缓动 | 默认参数（可调范围） | 参数写在哪（单点） | 降级（reduced-motion） |
| --- | --- | --- | --- | --- | --- |
| 转写气泡入场 | 新一段渲染到「讨论」流 | **复用** `@keyframes chat-enter`：透明度 0→1 + 上移 6px；`--msg-enter` 120ms + `--ease` | 沿用 120ms / 6px（0~200ms / 0~12px） | `global.css :root` 的 **r004 段**（既有，不新增参数） | `.chat-bubble { animation: none }`（`global.css:1562` 既有规则，转写气泡共用同类即自动降级） |
| 进房告知条自动收起 | 进房后计时 | 透明度 1→0 再移除；`--t-slow` 420ms | `--transcribe-notice-ms` = 30000（0~120000） | `global.css` **新 `:root` 段** | 直接移除（无过渡） |

**不做的动效**（防"顺手加"）：**新 keyframes**（复用 `chat-enter` 即可）、页面切换转场、气泡逐字打字机、气泡入场错峰级联、声波竖条的节奏改造（声波在 r009 已定，本轮不动）。

**界面文案口径**（沿用 r004/r005 既有口径；禁内部词：轮次 / 里程碑 / 检查点 / cp-NNN / 作业 / 考核）：

| 位置 | 原文 |
| --- | --- |
| 进房告知条 | 「本房间会把你说的内容转成文字，供大家与纪要使用」+ 按钮「知道了」/「关闭转写」 |
| 开关禁用（未配置 STT） | 「本房间未开启转写」 |
| 上传失败（一段丢了） | 不弹错，静默跳过（控制坞开关旁小字「本段未转写」，3 秒后消失） |
| 空转写列表 | 「还没有人说过话」 |

**一次视觉验收动作**（=验收示范）：打开 `/rooms/{id}/live` 并说话 10 秒 → 抽屉「讨论」里应出现带麦克风小图标的转写气泡（说话人名 + 时长），气泡底色与聊天气泡可区分；截图存 `%TEMP%\lg_r010\speech-bubble.png`。

## 4. 失败与边界

| 情况 | 处理 |
| --- | --- |
| STT 未配置 | 接口 503；前端开关禁用 + 文案「本房间未开启转写」；默认不伪装成功 |
| STT 调用失败 | 502 `STT_FAILED`；前端丢弃该段并继续下一段（不重试无限次） |
| 网络中断 | 前端最多重试 1 次；失败段不落库（宁可丢一段，不阻塞对话） |
| 静音/无人说话 | 能量门限跳过，不产生空转写（也省费用） |
| 房间结束 | 上传 409；已落转写仍可读、进纪要 |
| 重传同段 | `segment_index` 唯一索引 → 幂等忽略 |
| 隐私 | 音频不落盘；日志只记长度与耗时，不记文本；关闭后立即停传 |
| 说话人=本人 | 路径 B 天然保证；若日后换路径 A，用 `participant.identity` 映射 |

## 5. 教学契约

**场景一句话**：你在房间里正常说话，说的内容自动变成文字，落在「讨论」里，会后的纪要直接引用它——不用任何人打字。

| 项 | 内容 |
| --- | --- |
| 入口与命令名 | ① 控制坞开关：**「转写」**（默认开，本人关掉后本机记住）② 进房告知条按钮：**「关闭转写」/「知道了」** ③ 看文字的地方：抽屉 **「讨论」** tab 里的转写气泡（麦克风小图标）④ 回看入口：房间列表卡 **「讨论纪要」** |
| 输入与输出 | **输入**＝本端麦克风（`MediaRecorder` 每 `STT_SEGMENT_SECONDS`(8s) 一段；静音段按能量门限跳过，不产生空转写）。**输出**＝每段落库一条 `transcript`（说的人、开始时间、时长、文本），出现在「讨论」流与纪要素材里；**不保留音频** |
| 一次典型使用动作（3 步） | ① 进房看到告知条 → 点「知道了」（或点「关闭转写」表示本人不参与）② 正常说话，控制坞开关保持开启 ③ 打开抽屉「讨论」，看到自己那句话变成气泡（带时长，如 `0:08`） |
| 开发者视角扩展点 | ① **换 STT 供应商**：只改 `.env` 的 `STT_BASE_URL / STT_API_KEY / STT_MODEL`（Whisper 兼容协议），代码不动；② **调分段/上限**：`STT_SEGMENT_SECONDS / STT_MAX_SECONDS / STT_MAX_BYTES` 三个环境键；③ **换实现路径**：如将来改走官方 Agents 侧转写，`services/stt.py` 是唯一出口（ADR-0022 D3 的迁移点，只换这一层）；④ **语气/门限**：前端 `useTranscription` 的能量门限与重试次数（各一个常量） |
| 不承诺（本轮边界） | 不做说话人识别与跨端归属（说话人恒为本端采集者）；不做实时逐字显示（只出"一段完之后"的最终稿）；不做多语种切换（默认 `zh`，可用请求参数覆盖） |

## 6. 文档产出（硬产出）

需求单 + 本文 + ADR-0022 + 实现页/功能页 + README（`.env` 三键与演示路径）+ review。


## 9. 路径修订：Agents 侧识别 + 前端回传落库（最小演示，2026-09-20）

> **本节取代** §1~§4 中与「路径 B（本端上传音频）」相关的实现细节：迁移改为 010（§9.3.1）、后端不再需要 `STT_*` 才能工作（§9.3.4）、前端不再做 MediaRecorder 分段（§9.4）。**§4 失败与边界、§5 教学契约、§6 文档产出**中与 B 路径绑定的条目按本节口径改写。依据：`spike-01-path-a.md`（实测）+ `cr-02.md`（换轨 CR）+ `ADR-0023`（proposed）。
> 三条已核事实：`identity = user_id`（ADR-0011 条 2）、**LiveKit 房间名 = `rooms.id`**、建房可带 `RoomAgentDispatch`。

### 9.1 拓扑与运行形态（最小演示）

三个进程：后端 `:8000` + 前端 `:5173`（Vite）+ **转写 worker**（新，常驻；自带管理口 `:2077`）。
- worker 文件：`backend/agents/transcriber.py`；依赖清单：`backend/requirements-agents.txt`（`livekit-agents`，**不装进 `learningguide` 主环境**）；启动：`agents.bat`（激活 `lg_agents` 环境 → `python transcriber.py dev`）。
- 识别走 **LiveKit Inference**（免费档，`inference.STT("deepgram/nova-3", language="zh")`）→ **无需自备 STT key**；`.env` 里 `STT_BASE_URL/API_KEY` 降级为「B 路径专用，可为空」。
- 演示前置：先起 worker → 再建房/进房；探活 `curl http://127.0.0.1:2077` 或看日志 `registered worker`。
- **免费档护栏**：Inference STT 并发 5 条 → **演示 ≤3 人、单场 ≤30 分钟**；worker 侧 `MAX_SESSIONS=5`，超限只告警并跳过（不抛错）。

### 9.2 worker（`backend/agents/transcriber.py`，函数级）

```python
AGENT_NAME = "learning-guide-transcriber"          # 一行常量，派单与前端识别共用
MAX_SESSIONS = 5                                    # 免费档 STT 并发护栏

server = AgentServer()                              # cli.run_app(server) 起进程

@server.rtc_session(agent_name=AGENT_NAME)
async def entrypoint(ctx: JobContext) -> None:
    """被派单进房：订阅音频（AUDIO_ONLY），给「有音频轨的」参与者各开一个 AgentSession。"""

class Transcriber(Agent):
    def __init__(self, *, participant_identity: str) -> None:
        super().__init__(instructions="not-needed",
                         stt=inference.STT("deepgram/nova-3", language="zh"))
    async def on_user_turn_completed(self, turn_ctx, new_message) -> None:
        # 只转写、不回话、不跑 LLM
        raise StopResponse()

class TranscriberPool:
    def on_participant_connected(self, p) -> None      # 有音频轨才开会话；超过 MAX_SESSIONS → 告警跳过
    def on_track_subscribed(self, track, pub, p) -> None  # 后加入的音频轨补开会话
    def on_participant_disconnected(self, p) -> None   # 关会话 + drain
    async def _start_session(self, p) -> AgentSession   # room_options=RoomOptions(
                                                        #   audio_input=True, text_output=True,
                                                        #   audio_output=False, text_input=False,
                                                        #   participant_identity=p.identity)
```

- **关麦 = 不转写**：参与者静音后音频轨无声 → STT 无输出，无需额外逻辑（隐私承诺由这条承担）。
- **不做**：多语种切换、说话人分离、worker 自愈/监控、房主级开关。
- 前端如何知道"转写已开启"：**看房间里有没有 `agent-*` 参与者**（LiveKit SDK 天然可见，零后端改动）。

### 9.3 后端改造（函数级）

#### 9.3.1 迁移 `backend/app/db/sql/010_r010_agent_transcripts.sql`
```sql
ALTER TABLE transcripts ADD COLUMN IF NOT EXISTS external_id TEXT;   -- = LiveKit segment.id
CREATE UNIQUE INDEX IF NOT EXISTS ux_transcripts_external
  ON transcripts (room_id, external_id) WHERE external_id IS NOT NULL;
ALTER TABLE transcripts ALTER COLUMN segment_index DROP NOT NULL;    -- A 路径无"分段序号"
```
（`009_` 已应用，**不改历史迁移**。）

#### 9.3.2 `app/repositories/transcripts.py`
- `NewTranscript` 增 `external_id: str | None`；`insert_transcript` 走 `ON CONFLICT (room_id, external_id) DO NOTHING`（有 `external_id` 时；无则退回原 `segment_index` 唯一索引）。
- 新增 `get_by_external_id(conn, room_id, external_id) -> TranscriptRowWithName | None`。

#### 9.3.3 `app/services/transcripts.py`
```python
def ingest_segment(conn, actor, room_id, *, external_id: str, speaker_id: str, text: str,
                   started_at: datetime, duration_ms: int, language: str = "zh") -> tuple[TranscriptVO, bool]:
    """前端回传的**最终稿**文本段（A 路径）。
    权限：actor 必须是本房**活跃成员**；`speaker_id` 必须**也是本房成员**（含已离开）；
    房间 `ended` → 409 ROOM_ENDED（与上传口径一致）；
    幂等：(room_id, external_id) 冲突即返回已存在的行（created=False）——**谁先到谁落**。
    """
```
- `transcribe_segment`（B 路径音频上传）**保留不删**：`STT_MODE=backend` 时才被前端调用。

#### 9.3.4 `app/api/routers/transcripts.py` 与配置
| 接口 | 说明 |
| --- | --- |
| `POST /api/rooms/{id}/transcripts/segments`（**新增**） | JSON：`{externalId, speakerIdentity, text, startedAt, durationMs, language, final}`；`final=false` → **204 且不落库**；`final=true` → 201 `{transcript, created}` |
| `POST /api/rooms/{id}/transcripts`（保留） | B 路径音频上传，`STT_MODE=backend` 时才有意义 |
| `GET /api/rooms/{id}/transcripts`、`/conversation` | 不变 |
| `GET /api/stt/status`（**新增**） | `{mode, agentName, maxSessions}`；`mode` 取 `STT_MODE`（`agent` 默认 / `backend` / `off`） |
- `app/config.py`：新增 `stt_mode`（`STT_MODE`，默认 `agent`）、`stt_agent_name`（默认 `learning-guide-transcriber`）。
- `app/services/livekit.py`：新增 `dispatch_transcriber(room_id)`；`rooms.create_room` 在 `STT_MODE=agent` 时建房带 `agents=[RoomAgentDispatch(agent_name=...)]`；**已存在的房**用 `AgentDispatch` 补派单（演示前兜底，一次调用）。

### 9.4 前端改造

| 文件 | 改动 |
| --- | --- |
| `hooks/useTranscription.ts` | **重写**：`room.on(RoomEvent.TranscriptionReceived, (segments, participant))` → 渐进文本存本地态（`final=false` 原地替换）、`final=true` 时 ①渲染气泡 ②`POST /transcripts/segments`（`externalId=segment.id`、`speakerIdentity=participant.identity`）。**删除** MediaRecorder 分段/重传/能量门限 |
| `components/live/ConversationPanel.tsx` | `speech` 气泡：说话人名由 `identity → 成员显示名` 映射；时长显示 `durationMs` |
| `components/live/TranscribeNotice.tsx` | **文案改写**（隐私口径变化）：明确「说的话会被房间内的转写服务识别，音频会经过 LiveKit 云与识别服务商；关掉自己的麦克风即不参与转写」 |
| 控制坞「转写」开关 | 状态来源改为「房间里有无 `agent-*` 参与者」：有=「转写：开启」/无=「转写：未开启（不影响你说话）」；**去掉**"本端关转写上报"的旧语义（关麦即停） |
| 上报策略 | 默认**所有在线成员都上报收到的 final 段**（冗余 + 幂等，谁先到谁落）；若你要省请求，可改成"仅房主 + 说话人本人"（见待拍板 Q1） |

### 9.5 纪要与三源合一（不变）
`build_conversation` 三源合一照旧；纪要读 `transcripts` 表照旧（cp-4 预计零代码改动，只补用例与口径）。

### 9.6 边界与降级（最小演示）
| 情况 | 处置 |
| --- | --- |
| worker 不在线 | 前端显示「转写：未开启」，**不报错、不伪装**；不做 B 路径自动兜底（本轮） |
| 免费档额度/并发 | 演示 ≤3 人、单场 ≤30 分钟；`MAX_SESSIONS=5` 护栏；额度见 `spike-01-path-a.md` §8 |
| 音频隐私 | 如实告知（音频经 LiveKit Cloud 与供应商）；**不保留音频**（ADR-0022 D5 沿用） |
| 8 人满员 | 不做（会超免费档 5 并发） |

### 9.7 验收条目修订（在需求单 E 条目上替换/新增）

| 条目 | 新口径 |
| --- | --- |
| E2（改） | 三条分支：worker 在场 → 说话出渐进字幕并落库；不在场 → 前端提示且无报错；`STT_MODE=off` → 提示且不上报 |
| E3（改） | 幂等改为**同一 `segment.id` 多次上报只落一行**（含"三端同时上报"的并发用例） |
| E5（改） | 前端**不再有** MediaRecorder 分段与音频上传（`STT_MODE=agent` 时）；`STT_MODE=backend` 时旧路径仍可用 |
| E6（改） | `.env.example`：`STT_MODE` / `STT_AGENT_NAME` 新增；`STT_BASE_URL/API_KEY/MODEL` 标注「B 路径专用，可空」 |
| E13（新） | **3 人真机**：说话 5 秒内出现渐进字幕、定稿后库里 +1 行、三端内容一致、`speaker` 正确 |
| E14（新） | worker 不在场：前端显示"未开启"、控制台无未捕获异常、接口无 5xx |

### 9.8 cp 重新切分（原 §8 的 cp-2 起替换）

| cp | 内容 | 验收点 |
| --- | --- | --- |
| cp-2a | 迁移 010 + `ingest_segment` + `/transcripts/segments` + `/api/stt/status` + 派单能力（`services/livekit.py`）+ 用例（含并发幂等） | E2/E3/E6/E14（后端侧） |
| cp-2w | worker：`backend/agents/transcriber.py` + `requirements-agents.txt` + `agents.bat` + 探活与演示前置说明 | worker 起得来、被派单、3 人房识别成功 |
| cp-3 | 前端：监听渲染 + 上报 + 告知条文案 + 关麦语义 + 气泡 + 闸门状态 | E5/E13 |
| cp-4 | 纪要带转写（补用例与口径） | E7 |
| cp-5 | 收官：真机（3 人 10 分钟）+ 门禁四绿 + 教学页（含演示脚本与探活）+ review | E8/E11/E12 |

### 9.9 待实测项（诚实标注，实现时先取数）
1. 真 STT 下 `TranscriptionSegment.startTime/endTime` 是否有值（spike 用假 STT 时为 0）→ 影响 `started_at`/`duration_ms`；兜底：用收到时间与相邻段差值。
2. 免费档并发是"按参与者"还是"按活跃语音"占用（决定 3 人演示是否安全）。
3. `agent session minutes` 计费口径（每人一会话 vs 每房一会话）→ 看控制台账单确认。

## 10. 变更记录

| 日期 | 版本 | 改了什么 | 依据 |
| --- | --- | --- | --- |
| 2026-09-19 | v1 | 建页：逐文件函数签名与职责（数据层 / 后端 / 前端 / 失败与边界 / 文档产出） | 澄清单 Q1~Q12 |
| 2026-09-20 | v3 | **换轨修订**：新增 **§9 路径修订（Agents 侧识别 + 前端回传，最小演示）**，取代 §1~§4 中与路径 B 相关的实现细节；依据 `spike-01-path-a.md` / `cr-02.md` / `ADR-0023` | 你 2026-09-20「有免费档就行，只做最小程度演示，出设计方案」 |
| 2026-09-20 | v2 | 补 **§3.2 视觉契约**（3 个新令牌 + 动效清单 + 界面文案 + 一次视觉验收动作）与 **§5 教学契约**（场景/入口/输入输出/典型动作/扩展点/边界）；原 §5 文档产出顺延为 §6；状态 `approved` → **`draft`（等你读完再批）** | 你 2026-09-20「设计我都没看，看完回复」+ 界面类轮次的契约要求 |
