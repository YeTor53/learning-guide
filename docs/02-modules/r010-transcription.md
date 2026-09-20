---
title: r010 实现页：语音转文字并入讨论流（Agents 侧识别 + 前端回传落库）
description: 迁移 009/010、转写段接口与幂等键、会话数护栏、worker 结构与崩溃处置、前端监听渲染与令牌——决定性与实测事实源。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-20
---

<!-- overview -->
需求见 `docs/00-requirements/r010-transcription.md`；逐文件设计 `rounds/r010-transcription/design.md`（**§9 为换轨后口径**）；决定 **ADR-0023**（换轨，取代 ADR-0022 的 D1）；实测 `rounds/r010-transcription/spike-01-path-a.md`（含配额与成本）；验收 `rounds/r010-transcription/review.md`。
一句话：**识别在房间侧**（Agents worker 订阅音频 → LiveKit Inference → 官方通道注入房间），**落库仍走我方 HTTP**（前端把最终稿 POST 回来，谁先到谁落）。「关麦即不参与转写」。

## 1. 数据层（`app/db/sql/009_r010_transcripts.sql` + `010_r010_agent_transcripts.sql`）

| 面 | 要点 |
| --- | --- |
| 表 | `transcripts`：`id`（我方 `trs_*`）/ `room_id` / `speaker_id` / `segment_index` / `text` / `language` / `started_at` / `duration_ms` / `provider` / `model` / `created_at` |
| 迁移 009 | 建表 + `(room_id, speaker_id, segment_index)` 段唯一索引（B 路径幂等）+ 房间时间索引 |
| 迁移 010 | 加 `external_id`（= 官方 `segment.id`）+ 唯一索引 `(room_id, external_id)`；`segment_index` **放开 NOT NULL**（A 路径没有「第几段」） |
| 幂等两套键 | A 路径 = `external_id`（多端冗余上报天然去重）；B 路径 = `(room_id, speaker_id, segment_index)`。`insert_transcript` 按字段有无自动分派冲突目标 |
| 归属 | `speaker_id` 就是 LiveKit identity，而本项目 **identity = 我们 `user_id`**（ADR-0011 条 2）→ 零映射表 |
| 语义 | `provider='livekit'`、`model=<STT_AGENT_NAME>`；`duration_ms` 服务端兜底 `max(1, 上报值)`（假 STT 无起止时间时会是 1） |
| 实测 | 三人房 35 行 / 3 位说话人 / `external_id` 全非空 / `segment_index` 全空（review §3.5） |

## 2. 后端（4 个端点 / 5 个方法）

| 端点 | 行为 |
| --- | --- |
| `POST /api/rooms/{id}/transcripts/segments` | 前端回传**最终稿**；`final=false` → **204 丢弃**（中间稿不落库）；`final=true` → 201 `{transcript, created}`（`created=false` = 命中去重） |
| `GET /api/rooms/{id}/conversation?limit=` | **三源合一**（聊天 + 系统事件 + 语音），排序键 `(at, id)`；`speech.at` 取 `started_at`；`meta` 带 `durationMs/language/externalId` |
| `GET /api/rooms/{id}/transcripts` | 原 B 路径列表（保留不激活） |
| `GET /api/stt/status` | `{mode, agentName, maxSessions, segmentSeconds}`（前端只读 `mode`；`segmentSeconds` 是 B 路径遗留字段，见 review 未闭合 ⑨） |

| 函数 | 职责 |
| --- | --- |
| `services/transcripts.ingest_segment` | 权限（本房成员/管理）→ 房间状态（ended 409）→ **说话人必须是本房成员**（含已离开）→ 幂等（先查 `external_id`）→ 落库 |
| `services/transcripts.build_conversation` | 各取最近 `limit` 条消息与转写 → 合并 → `(at, id)` 正序 → 截断 |
| `services/transcripts._assert_can_read` | 转写/对话流的统一可见性（成员含已离开 / 管理 / 房间可 `ended`） |
| `services/livekit.ensure_transcriber` | 建房时派单（`CreateRoomRequest(agents=[RoomAgentDispatch(...)])`，房间已存在则退化为 `agent_dispatch.create_dispatch`）；**失败只记日志，不影响建房** |
| `scripts/dispatch_agent.py` | 给**已存在**的房间补派单（演示兜底） |
| 护栏 | 文本 ≤2000 字；`limit` 1~200；`durationMs` 0→1；说话人非成员 400；非成员读 403 |

## 3. 转写 worker（`backend/agents/transcriber.py`，**独立环境 `lg_agents`**）

| 部件 | 要点 |
| --- | --- |
| `entrypoint` | `@server.rtc_session(agent_name=STT_AGENT_NAME)`：被派单进房 → `connect(auto_subscribe=AUDIO_ONLY)` → 扫描已有参与者 |
| `TranscriberPool` | **只给发布了音频轨的参与者**开会话（没麦的人不开，省并发也省额度）；`MAX_SESSIONS=5`（免费档 Inference STT 并发上限）超限**告警跳过**；参与者离开即关会话 |
| `Transcriber(Agent)` | `on_user_turn_completed` 里 `raise StopResponse()` —— 只转写、不回话、不调 LLM |
| STT 档位 | `AGENT_STT=inference`（默认，LiveKit Inference `deepgram/nova-3`，**无需自备 key**）/ `fake`（离线桩，零配额，联调与演示降级） |
| 崩溃处置 | 实测崩过 1 次（LiveKit FFI panic，`timed out waiting for ReadyForRoomEventRequest`）→ `agents.bat` **自动重启** + 控制坞如实显示「未开启」（review 未闭合 ①） |
| 依赖 | `backend/requirements-agents.txt`（`livekit-agents==1.8.2` / `livekit-api==1.2.1`）——**不进主环境 `learningguide`** |

## 4. 前端

| 文件 | 要点 |
| --- | --- |
| `api/transcripts.ts` | `sttStatus` / `conversation` / `postSegment`（走 `request()` 统一封装） |
| `hooks/useTranscription.ts` | 监听 `RoomEvent.TranscriptionReceived` → `final=false` 进 `live`（渐进上屏）、`final=true` 进 `lines` 并**回传**（按 segment id 去重，失败可重试）；刷新时从 `/conversation` 补历史；`agentPresent` 判据 = `isAgentParticipant`（identity 前缀 + SDK kind），并加 **5 秒轮询兜底**（实测竞态：本端建连早于 agent 入场时事件漏刷） |
| `components/live/SpeechBubble.tsx` | 复用 `.chat-bubble` 外壳；左侧色条 + 麦克风图标 + 说话人；时长 ≤1s 不显示（不显示假的 0:00） |
| `components/live/TranscribeNotice.tsx` | 进房一次性告知（隐私口径如实）；自动收起时长读 CSS 令牌 `--transcribe-notice-ms`；「知道了」后本机记住 |
| `ChatPanel` | 三源合并渲染（聊天 + 系统 + 转写），末尾渲染渐进气泡「识别中…」 |
| `DeviceBar` | 只读 chip「转写：开启/未开启」（**不是按钮**，避免「点了没反应」） |
| `LiveStage` / `useOnlineIdentities` | 统一 `isAgentParticipant` 过滤——**转写 agent 不是房间成员，不进舞台格、不算在线成员**（真机发现的缺陷，cp-5 修） |
| 令牌 | 仅 3 个，全部在 `global.css` 的 r010 段：`--speech-bar-color` / `--speech-icon-size`(14px) / `--transcribe-notice-ms`(30000)；不新增 keyframes（复用 `chat-enter`） |

## 5. 纪要接线（`services/summary.py`）

- `build_summary_input` 增加 `speech_lines`（`[HH:MM] 名字（语音）：文本`，只取最终稿）+ `digest` 增加 `speech=` 计数。
- 用例：桩捕获给 LLM 的 messages，断言转写文本与「语音转写」段都在素材里（`test_transcription_feeds_summary_material`）。

## 6. 验证数字（2026-09-20）

| 项 | 结果 |
| --- | --- |
| 门禁 | `pytest` **156 passed**｜`smoke` **PASS 46/46**｜`tsc`/`build` exit 0（2010 modules / 3.92s） |
| 真机 E2E（3 人，假 STT，零配额） | worker 入场 **13.4s**；三端控制坞全「开启」；气泡 **32/33/35**；`errors: []`；`agent-在场` 后落库 35 行 |
| 幂等 | 后端日志 **56 次上报 → 201**，库里唯一 35 行 |
| 归属 | `speakers = [房主F, 乙F, 丙F]`（每端都能看到别人的话） |
| 截图 | `%TEMP%\lg_r010_e2e\shot-notice.png`、`shot-discussion.png`（含一次真机复看修复） |
| **音频路径（离线语音回归）** | `frontend/scripts/verify-transcription.py`：TTS 语音当麦克风 → 本端采集 RMS **0.214 / 0.273**；对端 4 秒收 **+35~43 KB**、`totalAudioEnergy` **+0.35~1.09**（非静音）→ **PASS** |
| 上报质量（该房） | 361 次上报全 201 → 唯一 96 行 / 4 说话人（冗余 3.76×）；该房请求全 2xx |
| 真实网络注意 | 本机**首连偶发超时换区**，实测最慢 **24.2s** → 演示前各端先预热进房一次 |

## 7. 扩展点

1. **换供应商/模型**：只改 worker 的 `AGENT_STT_MODEL`（`.env` 或环境变量）；B 路径则改 `STT_BASE_URL/STT_API_KEY/STT_MODEL`。
2. **换识别路径**（A ↔ B）：`STT_MODE=agent|backend|off`；两条路径共用同一张 `transcripts` 表与同一套幂等口径。
3. **调并发护栏**：worker 的 `AGENT_MAX_SESSIONS`（免费档 Inference STT 并发 5）。
4. **换实现细节**：前端渲染只在 `useTranscription` + `SpeechBubble`；服务端只经 `ingest_segment` 一个入口。

## 8. 遗留（如实）

未闭合 ①~⑩ 全表见 `rounds/r010-transcription/review.md` §5。要点：worker 稳定性（①，已加自动重启）｜`STT_MODE=off` 分支未验（②）｜渐进字幕在假 STT 下未采到样本（③，真 STT 已由 spike 证实）｜`duration_ms` 在假 STT 下恒为 1（④）｜`segmentSeconds` 语义待改（⑨）｜房主级转写开关、跨端说话人分离、B 路径前端未做（⑦）。

## 变更记录

| 日期 | 轮次 | 变更 | 依据 |
| --- | --- | --- | --- |
| 2026-09-20 | r013 `cp-4` | worker 自愈与可观测：`agents/retry.py` 纯函数重试；`entrypoint` 连接段 3 次重试 + 失败退出码 2；心跳带 `lastError` 并由 `/rooms/{id}/stt-status` 透出到控制坞芯片 hover | r013 需求单 E5/E6；`test_connect_retry.py` + 真机芯片 |

| 日期 | 轮次 | 改了什么 | 回链 |
| --- | --- | --- | --- |
| 2026-09-20 | r010 | 新建：语音转文字并入讨论流（换轨 Agents 侧识别 + 前端回传落库）的首个模块页 | `docs/rounds/r010-transcription/`；ADR-0023 |
| 2026-09-20 | r010 cp-6 | 补「音频路径」实测行与两点测量教训（WebRTC 统计代替 AudioContext；先等 connected 再测）+ 回归脚本入库 | `frontend/scripts/verify-transcription.py`；`changes.md` §3.6 |
