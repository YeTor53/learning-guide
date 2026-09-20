---
title: r011 台账（changes）：cp 切分、门禁数字与逐处改动
description: 本轮每处改动的「现在 → 改成 → 依据」与四项门禁实测数字；cp-1 为阶段 1 文档。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-20
---

<!-- overview -->
行号基准 `main` = `96b1153`。数字标注「本轮实测」或「历史（引 changes/提交）」。

## 1. cp 台账

| cp | 内容 | 状态 | 提交 | 验收点 |
| --- | --- | --- | --- | --- |
| cp-r011-1 | 阶段 1 文档：需求单 + design（逐文件清单）+ 人工剧本（MV-1~MV-9）+ 台账/审查骨架 + 需求索引行 | **完成 2026-09-20** | 见 cp-1 提交 | 文档先行 |
| cp-r011-2 | A 组项目级活页：README 状态与数字 + 演示路径补转写/焦点步；AGENTS.md 数字与容量口径；覆盖页整页重写去重 | **完成 2026-09-20**（2 提交：`fe336e2`、`4f361eb`） | 见 cp-2 提交 | E1 |
| cp-r011-3 | A 组轮次台账与验收清单回勾：r002 §4 **36 条**（[x] 32 / [~] 4 转 MV-1/MV-8/MV-10）、r005 §5 **8 条**（[x] 7 / [~] 1）、r006 语录数字口径注、r010 §6 矩阵补回归脚本、人工剧本加 MV-10 | **完成 2026-09-20** | 见 cp-3 提交 | E1/E2/E3/E9/E10 |
| cp-r011-4 | B 组功能增量：满员自动拒待批申请（批量 `rejected` + 汇总系统消息）+ 邀请码入口（顶栏常驻）与未登录 `returnTo` 闭环 + 等待页文案 + 使用者教学页 | **完成 2026-09-20** | 见 cp-4 提交 | E4/E5 |
| cp-r011-5 | B 组 worker 健康上报（心跳端点 + 内存态 + 芯片按房判据）+ C 组用例（`STT_MODE=off` ×2、满员自动拒 ×3、心跳 ×3）+ 既有用例按新语义更新 | **完成 2026-09-20**（pytest **164 passed**、build exit 0） | 见 cp-5 提交 | E6/E7 |
| cp-r011-6 | 焦点规则收窄：说话不再获得焦点（删说话者档 + 删 `useStableSpeaker` 死代码）+ ADR-0014/模块页/教学页/剧本同步 | **完成 2026-09-20** | 见 cp-6 提交 | E11 |
| cp-r011-7 | 门禁与取证收官：四项门禁 + 索引/矩阵回填 + review 定稿 | 待做 | — | E8/E9 |

## 2. 门禁数字

| cp | pytest | smoke | tsc --noEmit | npm run build |
| --- | --- | --- | --- | --- |
| cp-0（进入本轮前，历史） | 156 passed（r010 review §5b） | 46/46（历史） | exit 0（历史） | exit 0（历史） |
| cp-1/1b（纯文档） | 未跑（无代码改动） | 未跑 | 未跑 | 未跑 |
| cp-2/3（纯文档） | 未跑（无代码改动） | 未跑 | 未跑 | 未跑 |
| cp-5（本轮，2026-09-20） | **164 passed**（49.53s；+8：自动拒 3 / 心跳 3 / off 2） | 待 cp-6 跑 | exit 0 | exit 0（2010 modules，4.05s） |
| cp-6（焦点收窄，2026-09-20） | 164 passed（未改后端逻辑，复跑见 cp-7） | 待 cp-7 跑 | exit 0 | exit 0 |
| cp-7（收官，待填） |  |  |  |  |

## 3. 逐处改动（现在 → 改成 → 依据）

（cp-2 起逐格填写；格式：`文件` → 现在是什么 → 改成什么 → 依据）

## 3.1 cp-3 回勾统计（实测）

| 文件 | 条目 | [x] | [~] 转人工剧本 |
| --- | --- | --- | --- |
| `docs/00-requirements/r002-livekit-room.md` §4 | 36 | 31 | 5（MV-1 ×2、MV-8、MV-10 ×2，另有 3 条按新口径标注） |
| `docs/00-requirements/r005-fix-capacity.md` §5 | 8 | 7 | 1（MV-10） |

## 3.2 cp-4 逐处改动（本轮实测）

| 文件 | 现在 → 改成 | 依据 |
| --- | --- | --- |
| `backend/app/repositories/rooms.py` | 新增 `reject_pending_requests(conn, room_id, decided_by, at)`：批量把该房 `pending` 申请置 `rejected` 并返回行数（与 `cancel_pending_requests` 的区别是状态语义为「被拒」） | r011 B1 |
| `backend/app/services/rooms.py` | 新增 `_auto_reject_pending(conn, room, actor)`：批量拒绝 + 一条汇总系统消息（0 条不写）；`request_join` 满员分支调用；`approve_join_request` 满员分支改为「**先提交清理、出事务后再抛 409**」（原实现 raise 会回滚，清理会作废） | r011 B1 + design §5 边界 |
| `frontend/src/pages/WaitingPage.tsx` | rejected 文案补「或房间已满被系统自动拒绝」 | r011 B1 |
| `frontend/src/components/NavBar.tsx` | `top-actions` 增常驻 `邀请码加入` → `/join`（未登录也可见） | r011 B2 |
| `frontend/src/pages/JoinByCodePage.tsx` | 未登录时主按钮改「去登录并加入」（跳 `/login?returnTo=/join?code=…&auto=1`）；带 `auto=1` 回来在登录后**自动加入一次**（`useRef` 防重复） | r011 B2 |
| `docs/tutorials/r011-invite-entry-and-capacity.md` | 新增使用者教学页（两条入口路径 / 未登录闭环 / 满员口径） | 覆盖矩阵 C 件套 |

## 3.3 cp-5 逐处改动（本轮实测）

| 文件 | 现在 → 改成 | 依据 |
| --- | --- | --- |
| `backend/app/services/stt.py` | 新增内存态心跳登记：`_HEARTBEATS` / `record_heartbeat` / `last_heartbeat` / `heartbeat_age_seconds` / `latest_heartbeat` / `HEARTBEAT_FRESH_SECONDS=15` | r011 B3（甲方案：零迁移） |
| `backend/app/schemas/transcripts.py` | 新增 `SttHeartbeatIn`（roomId / workerId / sessions） | 同上 |
| `backend/app/api/routers/transcripts.py` | 新增 `agent_heartbeat_token()`、`POST /stt/heartbeat`（HMAC 鉴权，错/缺 401）、`GET /rooms/{id}/stt-status`（按房心跳 + `fresh`）；`GET /stt/status` 追加 `lastHeartbeatAt` / `lastHeartbeatRoomId`（向后兼容） | 同上 |
| `backend/agents/transcriber.py` | 新增 `_session_secret()`（env → 仓库根 `.env`）、`_post_heartbeat_sync()`、`_heartbeat_loop()`（每 5 秒，子线程发，失败只记 debug）；`TranscriberPool.sessions()` 只读访问器；`entrypoint` 起心跳任务并在 shutdown 取消 | 同上 |
| `frontend/src/api/transcripts.ts` | 新增 `RoomSttStatus` 与 `roomSttStatus(roomId)` | 同上 |
| `frontend/src/hooks/useTranscription.ts` | 5 秒轮询本房心跳 → 暴露 `heartbeatAt` / `heartbeatFresh`（15 秒窗口） | 同上 |
| `frontend/src/components/live/DeviceBar.tsx` | 芯片提示补「最后心跳 X 秒前 / 本房还没有心跳记录」 | 同上 |
| `frontend/src/pages/RoomLivePage.tsx` | 芯片判据改为 `agentPresent \|\| heartbeatFresh`（LiveKit 参会者事件漏刷时心跳兜底） | 同上 |
| `backend/tests/test_stt_heartbeat.py`（新） | 3 条：缺/错令牌 401、心跳出现在本房与全局状态、无心跳时为 null | E6/E7 |
| `backend/tests/test_room_full_auto_reject.py`（新） | 3 条：满员新申请 → 全部 pending 变 rejected + 汇总系统消息；批准被挡时清理不被回滚；`?status=pending` 清空 | E4 |
| `backend/tests/test_transcript_segments.py` | 2 条：`STT_MODE=off` 不派单（真实 `ensure_transcriber` + 打桩 `_run`）；`/stt/status` 如实报 off | E7 |
| `backend/tests/test_rooms_service.py` | 既有 `test_approve_rejected_when_full` 断言改为「被自动拒绝」（原断言"保持 pending"是旧语义） | 行为变更（同 E4） |
| `.env.example` | 追加注释：`AGENT_BACKEND_URL` / `AGENT_HEARTBEAT_SECONDS`（可选键） | 同上 |

### cp-5 如实边界
- `STT_MODE=off` 的语义 = **后端不派单 + 前端显示未开启**；后端回传端点未加「off 就拒收」的硬闸（本轮不改行为），端到端「无气泡、库内不新增」由 **MV-7** 人工核对。
- 心跳为**进程内存态**：后端重启即清空（不伪装），前端此时按「无心跳 + LiveKit 在场」判据显示。

## 3.4 cp-6 逐处改动（焦点规则收窄，L2）

| 文件 | 现在 → 改成 | 依据 |
| --- | --- | --- |
| `frontend/src/components/live/LiveStage.tsx` | 焦点身份由 `screenOwnerId ?? 手动焦点 ?? stableSpeaker` 改为 `screenOwnerId ?? 手动焦点 ?? null`；删 `useStableSpeaker` 引用；`speaking` 视觉高亮保留 | 你 2026-09-20「说话不会获得焦点！只有举手！或房主权力！」 |
| `frontend/src/hooks/useStableSpeaker.ts` | **删除**（改后零引用死代码；历史见 git） | r011 补正轮纪律（零引用死代码可删） |
| `docs/03-decisions/r004-adr-0014-focus-share-priority.md` | 决策表第 3 档标废止；理由段与后果段同步；追加变更记录 | L2 需记 ADR |
| `docs/02-modules/r009-focus-system-features.md`、`r009-focus-system.md` | 现状口径改写 + 变更记录 | 文档=代码 |
| `docs/00-requirements/r009-focus-system.md`、`rounds/r009-focus-system/motion-design.md` | 只加**指路行**（已收官轮次不回改正文） | 复验纪律 |
| `docs/tutorials/r009.5-r008-r009-user-guide.md` | 「规则一句话」改为新链条 | 教学页是活页 |
| `docs/rounds/r011-debt-backfill/manual-verification.md` | 新增 **MV-11**；**MV-5 作废**（说话不再夺焦点，无对象） | 取证口径 |

## 4. 未做 / 如实说明

- 本轮**不含** r012（超管 / 管理后台 / 全服大屏聊天）、部署与录屏、录制的实现。
- 演示库残留按你口径「开发结束后统一清」，本轮只登记不执行。
- 人工剧本 MV-1~MV-9 由你执行；未跑之前本轮相关验收条目一律标「未取证」。

## 5. 分支与交接

| 项 | 值 |
| --- | --- |
| 分支 | `req/r011-debt-backfill`（从 `main` = `96b1153` 开出） |
| 进入本轮前的 `main` | `96b1153`（`round-r010-done`；r005~r010 + r009.5 均已合并、tag 齐） |
| 合并顺序 | 本轮从最新 main 开出 → 合入时无前置未合并轮次 |
