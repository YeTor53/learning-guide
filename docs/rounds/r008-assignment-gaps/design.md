---
title: r008 设计：纪要链路、限时邀请、语音转文字
description: 逐文件函数级设计（迁移、仓储、服务、路由、前端页与钩子、外部调用失败语义）。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
需求与验收见 `docs/00-requirements/r008-assignment-gaps.md`。外部调用沿用 ADR-0011 条 4 语义：**外部失败不回滚业务事实**，失败另立状态并记原因；`services/summary.py`、`services/transcripts.py`、`services/livekit.py` 是本仓仅有的三个外部出口。

## 1. 数据层

### 1.1 迁移 `007_r008_session_summaries.sql`

```sql
CREATE TABLE IF NOT EXISTS session_summaries (
  id           TEXT PRIMARY KEY,
  room_id      TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
  status       TEXT NOT NULL CHECK (status IN ('ready','failed')),
  provider     TEXT NOT NULL DEFAULT '',
  model        TEXT NOT NULL DEFAULT '',
  input_digest TEXT NOT NULL DEFAULT '',
  content      TEXT NOT NULL DEFAULT '',
  error        TEXT,
  created_by   TEXT REFERENCES users(id),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_session_summaries_room ON session_summaries (room_id);
```

### 1.2 迁移 `008_r008_transcripts.sql`

```sql
CREATE TABLE IF NOT EXISTS transcripts (
  id          TEXT PRIMARY KEY,
  room_id     TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
  user_id     TEXT NOT NULL REFERENCES users(id),
  status      TEXT NOT NULL CHECK (status IN ('ready','failed')),
  text        TEXT NOT NULL DEFAULT '',
  error       TEXT,
  duration_ms INTEGER NOT NULL DEFAULT 0,
  seq         INTEGER NOT NULL DEFAULT 0,
  provider    TEXT NOT NULL DEFAULT '',
  model       TEXT NOT NULL DEFAULT '',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS ix_transcripts_room ON transcripts (room_id, created_at);
```

## 2. 后端

### 2.1 `app/schemas/summary.py`

```python
class SessionSummaryVO(CamelModel):
    id: str; room_id: str; status: str; provider: str; model: str
    input_digest: str; content: str; error: Optional[str]
    created_by: Optional[str]; created_at: datetime; updated_at: datetime

class SummaryEnvelope(CamelModel):
    summary: Optional[SessionSummaryVO]      # 未生成 = None
```

### 2.2 `app/schemas/transcripts.py`

```python
class TranscriptVO(CamelModel):
    id: str; room_id: str; user_id: str; display_name: str
    status: str; text: str; error: Optional[str]
    duration_ms: int; seq: int; created_at: datetime

class TranscriptListEnvelope(CamelModel):
    transcripts: list[TranscriptVO]
```

### 2.3 `app/repositories/summaries.py`

```python
def upsert_summary(conn, *, summary_id, room_id, status, provider, model,
                   input_digest, content, error, created_by) -> None
    """按 room_id 覆盖写（唯一索引）：created_at 保留首次、updated_at = clock_timestamp()。"""
def get_summary(conn, room_id) -> Optional[SessionSummaryRow]
def get_transcript_seq(conn, room_id, user_id) -> int
def insert_transcript(conn, *, row) -> None
def list_transcripts(conn, room_id, *, user_id: Optional[str] = None) -> list[TranscriptRowWithName]
```

### 2.4 `app/repositories/rooms.py`（增量）

```python
def insert_invite(conn, *, invite) -> None
def get_invite_by_code(conn, code) -> Optional[InviteRow]      # 由 service 在事务内 FOR UPDATE
def bump_invite_used(conn, invite_id) -> int                   # used_count += 1
def list_invites(conn, room_id) -> list[InviteRow]
```

### 2.5 `app/services/summary.py`

```python
def build_summary_input(conn, room_id) -> SummaryInput
    """素材：房间（topic_label/title/description/host）＋在册成员（角色/是否在场）＋
       最近 200 条消息（含系统消息）＋最近 200 条 ready 转写；同时产出 digest 字符串。"""
def render_messages(payload: SummaryInput) -> list[dict]
    """OpenAI 兼容 messages：[system: 中文纪要写作指令, user: 素材]（要求：分节、要点+争议+待办、不编造）。"""
def generate_summary(conn, actor, room_id, *, client=None) -> SessionSummaryVO
    """权限 Host/Moderator（房间可 ended）。锁房间行 → 素材 → 调 LLM →
       ready：upsert + 返回；调用失败/空内容：upsert failed + 抛 AppError(SUMMARY_FAILED, 502)；
       未配置密钥：不落库，抛 AppError(LLM_NOT_CONFIGURED, 503)。"""
def get_summary(conn, actor, room_id) -> Optional[SessionSummaryVO]
    """可见性：在册成员（含历史）或 Host/Moderator；否则 403。"""
def call_llm(messages, settings) -> str
    """唯一外部出口：aiohttp（已有依赖）POST {LLM_BASE_URL}/chat/completions，60s 超时，
       非 200 或空内容 → LlmError；不 import repositories、不做权限判断（同 livekit.py 纪律）。"""
```

### 2.6 `app/services/transcripts.py`

```python
def transcribe_chunk(conn, actor, room_id, audio: bytes, filename: str,
                     duration_ms: int, *, client=None) -> TranscriptVO
    """权限：在册成员；房间 ended → 409。未配置 STT → 503 STT_NOT_CONFIGURED（不落库）。
       成功 insert ready + 返回；STT 失败 insert failed（记 error）+ 抛 AppError(STT_FAILED, 502)。"""
def list_transcripts(conn, actor, room_id) -> list[TranscriptVO]
    """本人可见自己的；Host/Moderator 可见全部；其他成员仅见自己。"""
def call_stt(audio, filename, settings) -> str
    """POST {STT_BASE_URL}/audio/transcriptions（multipart：file + model + language=zh），60s 超时。"""
```

### 2.7 `app/services/invites.py`

```python
def create_invite(conn, actor, room_id, *, ttl_minutes=1440, max_uses=1) -> InviteVO
    """权限 Host/Moderator；房间必须 active（ended → 409）；ttl 1~10080 分钟、max_uses 1~50（越界 400）；
       code 8 位小写、唯一索引冲突重试 3 次。"""
def accept_invite(conn, actor, code) -> InviteAcceptResult
    """校验 存在/未过期/未用尽/房间 active（否则 400 INVITE_INVALID）；已在册 → 幂等 200（不 +1）；
       满员 → 409 ROOM_FULL；否则建在册成员 + used_count+1 + 系统消息「X 通过邀请链接加入」。"""
def list_invites(conn, actor, room_id) -> list[InviteVO]
```

### 2.8 路由

```python
# app/api/routers/summary.py
POST /api/rooms/{room_id}/summary           → 生成/重生（Host/Moderator）201
GET  /api/rooms/{room_id}/summary           → 查看（成员/管理身份）200；未生成 data.summary=null
# app/api/routers/transcripts.py
POST /api/rooms/{room_id}/transcripts       → multipart 上传音频片段（在册成员）201
GET  /api/rooms/{room_id}/transcripts       → 列表 200
# app/api/routers/invites.py
POST /api/rooms/{room_id}/invites           → 生成（Host/Moderator）201
GET  /api/rooms/{room_id}/invites           → 列表（Host/Moderator）200
POST /api/invites/{code}/accept             → 凭码加入 201（幂等时 200）
```

### 2.9 配置与错误码

```python
# config.py：stt_base_url / stt_api_key / stt_model（可选；缺失=对应能力 503）
# errors.py：SUMMARY_FAILED / LLM_NOT_CONFIGURED / STT_FAILED / STT_NOT_CONFIGURED / INVITE_INVALID
```

## 3. 前端

| 文件 | 职责 |
| --- | --- |
| `api/summary.ts` | `generate(roomId)` / `get(roomId)` / `listTranscripts(roomId)` / `uploadTranscript(roomId, blob, ms)` / `createInvite(roomId, ttl, uses)` / `acceptInvite(code)` |
| `pages/RoomSummaryPage.tsx`（新，`/rooms/:id/summary`） | 房间信息 + 纪要正文（`white-space: pre-wrap`）+（有权者）生成/重新生成 + 未配密钥提示 + 转写片段折叠区 |
| `components/RoomCard.tsx` | 已结束房间加「讨论纪要」入口 |
| `components/InvitePanel.tsx`（新，抽屉第三 tab「邀请」） | 生成（有效期/次数）+ 复制 `/join?code=` + 列表（到期/已用） |
| `pages/JoinByCodePage.tsx`（新，`/join?code=`） | 输入/预填邀请码 → 接受 → 直接进房间；错误明确（过期/用尽/满员） |
| `hooks/useTranscription.ts` | 房内「转写」开关：`MediaRecorder` 15s 分段 → `uploadTranscript` → 本地追加片段；未配置时禁用并提示 |
| `components/live/TranscriptPanel.tsx` | 抽屉第四 tab「转写」：片段列表（本人/管理身份） |

## 4. 失败与边界

| 情况 | 行为 |
| --- | --- |
| LLM 未配置 / 超时 / 空内容 | 503 `LLM_NOT_CONFIGURED` / 502 `SUMMARY_FAILED`（写 failed 行，可重试覆盖） |
| 同房间并发生成两次 | 锁房间行串行；后到者覆盖同一行，`updated_at` 前进 |
| 房间已结束后生成 | 允许（纪要本就在结束后看） |
| 邀请过期/用尽/非法 | 400 `INVITE_INVALID`（前端原样展示服务端 message） |
| 邀请码撞库 | 唯一索引 + 重试 3 次 |
| STT 未配置 | 503 `STT_NOT_CONFIGURED`；前端「转写」按钮禁用 + 提示 |
| 转写片段过大 | 单段上限 10MB / 60 秒（超出 400）；前端 15 秒切段 |
| 隐私 | 转写默认关闭、本人主动开；文本仅本人 + Host/Moderator 可见 |

## 5. ADR 分配

| ADR | 主题 |
| --- | --- |
| ADR-0018 | 纪要落 `session_summaries`（一间房一份、覆盖式重生、失败留痕、外部失败不改业务事实） |
| ADR-0019 | 邀请直接成为在册成员（跳过等候室、仍受容量上限） |
| ADR-0020 | 转写按本端麦克风分段（非服务端混音录制）；可见性 = 本人 + 管理身份 |

## 6. 变更记录

| 日期 | 版本 | 改了什么 | 依据 |
| --- | --- | --- | --- |
| 2026-09-19 | cp-0 | 建页：三件需求的函数级设计、失败边界、ADR 分配 | 你 `Q1=1` + 「再加一个语言转文字需求」 |
