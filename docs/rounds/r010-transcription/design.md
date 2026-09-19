---
title: r010 函数级设计：语音转文字并入讨论流（路径 B + 官方协议）
description: 逐文件的函数签名与职责——STT 唯一出口、转写落库、三源合一对话流、前端默认开启与分段上传。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
需求 `docs/00-requirements/r010-transcription.md`；调研 `research-01/02.md`；决定 ADR-0022。**未批不动代码。**

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

样式令牌（`global.css`）：`--speech-bubble-bg`、`--speech-icon-size`、`--transcribe-notice-ms`（告知条自动收起），可单点调。

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

## 5. 文档产出（硬产出）

需求单 + 本文 + ADR-0022 + 实现页/功能页 + README（`.env` 三键与演示路径）+ review。
