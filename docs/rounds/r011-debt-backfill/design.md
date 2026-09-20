---
title: r011 设计：欠账补正与三处授权的功能增量（逐文件改动清单）
description: A 组文档回填、B 组满员自动拒/邀请码入口/worker 健康上报的函数级设计、C 组用例与 D 组人工剧本清单；含 L0~L3 定性与失败边界。
type: design
status: draft
owner: 陀梓皓
updated: 2026-09-20
---

<!-- overview -->
行号基准：`main` = `96b1153`（round-r010-done，r005~r010 已合）。
本页只写**改哪个文件的哪个函数/哪个章节、改成什么、依据是什么**；不改规范、不引入新依赖。

## 0. 本轮定性

| 组 | 项 | 级别 | 依据 |
| --- | --- | --- | --- |
| A | 文档回填（README / AGENTS / coverage / 需求单勾选 / 索引） | **L0** 纯文档 | 修正与实现不符的表述，不改行为 |
| B1 | 满员时自动拒绝该房待批申请 | **L2** 行为变更 | 你 2026-09-20 拍板「在等待的自动拒绝」+ 授权原话「r011」 |
| B2 | 邀请码入口 + 未登录 `returnTo` 闭环 | **L1** 界面增量 | 同上（补作业必做项的界面缺口） |
| B3 | worker 健康上报 | **L3** 新增接口 + 状态契约 | 同上；契约新增字段需在本页 §6 登记 |
| C | 用例补齐（`STT_MODE=off`、满员自动拒） | **L0** | 只加测试 |

## 1. A 组：逐文件改动清单（纯文档）

| 文件 | 现在是什么 | 改成什么 | 依据 |
| --- | --- | --- | --- |
| `README.md` | 状态段写「r002 已完成并合入 main」；`schema_migrations 7`、`pytest 124 项`；演示路径 9 步缺 r009/r010 | 状态段改为「r005~r010 + r009.5 已合入 main、round tag 齐」；数字改 `schema_migrations 10`、`pytest 156 项`（或改为不带数字只给命令）；演示路径补「焦点系统（举手→给焦点→退出焦点）」「语音转写（先起 agents.bat，控制坞 13 秒内显示『转写：开启』）」「邀请码入口（顶栏）」三步 | r010 review §5b 实测 156/46/迁移 10；本轮 E8 |
| `AGENTS.md` | §「r002 起新增的验证命令」硬编码 `95 项` / `PASS 22/22`；§现状口径写「容量按**在场人数**在**取票时**校验」 | 数字改为命令 + 括号内实测值（156 / 46-46）；容量口径改为「**本库在册成员**（ADR-0016 取代 ADR-0012 的 D1/D2/D3/D5）」 | ADR-0016；r010 review §5b；r004 redirect-01 已登记漂移 |
| `docs/00-project/assignment-a-coverage.md` | 页内出现**两组** §5/§6，§7「加分项现状」与 §3 重复；结论数字停在 r008（124 / 迁移 7） | 整页重写：单一 §1 结论（必做 15/15、加分 0/5 全绿但录制经你决定不做、交付物 3/4 待你填两格）、§2 必做逐条（README 一条改判「部分」并写清缺什么）、§3 加分、§4 交付物、§5 建议下一步、§6 变更记录；删除重复段 | 本轮审计（题目原文 81 段逐条比对） |
| `docs/00-requirements/r002-livekit-room.md` §4 | **36 条** `- [ ]` 全未勾 | 逐条改为 `- [x]`（附依据：文件:行 / 用例名 / 命令输出）或改为 `- [~]` 并注明「转 MV-x（人工剧本）」/「口径已变：见 r005/ADR-0016」 | 本仓习惯：验收清单必须逐条给实现位置 + 证据（AGENTS.md 硬规矩 7） |
| `docs/00-requirements/r005-fix-capacity.md` §4 | **8 条** `- [ ]` 全未勾 | 同上（E1~E8 依据取自 `rounds/r005-fix-capacity/review.md` 与 changes 的实测数字） | 同上 |
| `docs/rounds/r006-ui-sync-polish/review.md` | 同页 E7 写「12 条」、E11 写「46 条 / 7 组」 | E7 数字后加注「（cp-3 口径；cp-7 起 46 条 / 7 组，见 E11）」；未闭合清单第 5 条同步 | cp-7 提交信息与 `changes.md` §1 |
| `docs/00-requirements/r010-transcription.md` §6 | 覆盖矩阵缺 cp-6 产物 | 增一行：`frontend/scripts/verify-transcription.py`（离线语音回归，cp-6，landed） | `changes.md` §1 cp-6 行 |
| `docs/00-project/global-roadmap.md` | §7 第 10 条写「@ ace6720」「cp-1~cp-5 + 补正 cp-5b/5c」；§9 无 r011/r012 行 | §7 第 10 条改为「已合入 main（`96b1153`、`round-r010-done`），cp-1~cp-6 + 补正 cp-5b/5c/5d 全落，复验 156/46」；§7 追加第 12/13 条（r011 进行中、r012 待开）；§9 增 r011 授权例外行、r012 超管行 | 本轮实测 git 事实 |
| `docs/00-requirements/README.md` | 索引无 r011 行；r009.5/r010 仍写「待合并」 | 加 r011 行；r009.5/r010 状态改「已合并（`96b1153`）」，完成 tag 列填 `round-r009.5-done` / `round-r010-done`；合并顺序注改为「r005→…→r010 均已合入」 | `git tag --list` 实测 |
| `docs/README.md` | §2「当前轮/下一轮」停在旧口径；§6 最新快照为 r010（137 页） | §2 两行改为 r011（补正中）/ r012（待开）；§6 追加本轮快照（保留 r010 快照） | 本仓习惯：快照保留历史 |

## 2. B 组：函数级设计

### B1 满员时自动拒绝该房待批申请（L2）

现状（`backend/app/services/rooms.py`）：
- `request_join`（:350）：容量判定在 :364-367 —— 已满时写一条系统消息「房间已满（上限 N 人），本次申请未通过」并返回 `RoomFullNotice`（路由转 409 `ROOM_FULL`）；**不动已有的 pending 申请**。
- `approve_join_request`（:406）：:421-422 满员时直接 `raise AppError(ERR_ROOM_FULL, …, 409)`。

改动：
1. `backend/app/repositories/rooms.py` 新增（紧邻 `cancel_pending_requests` :414）：
```python
def reject_pending_requests(conn: Connection, room_id: str, reason: str, decided_by: str, at: datetime) -> int:
    """把该房所有 pending 申请置为 rejected（同事务内批量更新），返回受影响行数。
    只改 join_requests.status/decided_at/decided_by/decide_reason，不碰 room_members。"""
```
（SQL：`UPDATE join_requests SET status='rejected', decided_by=%s, decided_at=%s, decide_reason=%s WHERE room_id=%s AND status='pending'`；`decide_reason` 若表内无此列 → 复用现有 `cancel_pending_requests` 的列集合，不新增列，避免迁移。）
2. `backend/app/services/rooms.py` 新增模块级私有函数：
```python
def _auto_reject_pending(conn: Connection, room: RoomRow, actor: UserVO) -> int:
    """满员时清理该房待批申请：批量置 rejected + 一条汇总系统消息（n>0 才写）。返回被拒条数。"""
```
3. 调用点（两处，都在房间行锁内）：
   - `request_join`：:367 返回 `RoomFullNotice` 之前调用 `_auto_reject_pending(conn, room_row, actor)`；系统消息顺序 = 原「本次申请未通过」→ 新「n 条待批申请已自动拒绝」。
   - `approve_join_request`：:422 `raise` 之前调用同一函数（同一事务，异常前已提交？→ **注意**：该路径 `raise` 会回滚事务 ⇒ 改为先 `conn.commit()` 再 raise，或在 raise 前用 savepoint。设计取「先 commit 后抛」并写明理由：拒绝申请属独立事实，不能因批准失败被回滚）。
4. 响应/契约：`POST /rooms/{id}/join-requests` 401/403/409 形状不变（409 `ROOM_FULL`），仅**多一条系统消息**；`GET /rooms/{id}/join-requests?status=pending` 结果会变少（被自动拒）。
5. 前端（`frontend/src/pages/WaitingPage.tsx`）：已有 `state === 'rejected'` 分支（:107/:118/:162）——只核对文案是否含原因；若只有「已拒绝」→ 补一句「（房间已满，系统自动拒绝）」。等待页轮询周期不变。

### B2 邀请码入口 + 未登录闭环（L1）

1. `frontend/src/components/NavBar.tsx`：`top-actions` 区内（`user ? 显示名 : 登录/注册` 之前）新增常驻入口：
```tsx
<Link className="link-plain" to="/join">邀请码加入</Link>
```
（`CRUMBS` 保持只做面包屑；入口对未登录也可见 —— 这是作业必做「邀请」项的界面补漏。）
2. `frontend/src/pages/JoinByCodePage.tsx`：
   - 新增：未登录时的主按钮改为「去登录并加入」，`onClick` → `navigate('/login?returnTo=' + encodeURIComponent('/join?code=' + code.trim()))`（`code` 为空则 `returnTo=/join`）。
   - 新增自动提交：`returnTo` 带回 `&auto=1`，页面在 `user && auto === '1' && code.trim()` 时自动调用一次 `accept.mutate()`（用 `useRef` 只触发一次，避免 React 严格模式重复提交）。
   - 保留：错误提示原样显示服务端 message（过期 / 用尽 / 满员 / 乱码）。
3. 注册路径：`RegisterPage.tsx` 已透传 `returnTo`（`LoginPage.tsx:8-12` 的 `safeReturnTo` 同款）→ 只核对，不改逻辑。
4. 无前端测试框架（本仓既有约束）：B2 的证据 = MV-9 人工核对 + `tsc`/`build` 绿。

### B3 worker 健康上报（L3）

现状：芯片「转写：开启」来自 LiveKit 侧 agent 参会者（`frontend/src/hooks/useTranscription.ts:102-118`，`isAgentParticipant` + 5 秒定时重算）；`/api/stt/status` 只回 `mode/agentName/maxSessions/segmentSeconds`（`backend/app/api/routers/transcripts.py:101-115`）。worker 崩溃时界面只能说「未开启」，说不出「最后活动于何时」。

建议形态（甲，零迁移）：
1. worker 侧 `backend/agents/transcriber.py`：
```python
async def _heartbeat_loop(room_id: str, worker_id: str) -> None:
    """每 5 秒向后端 POST /api/stt/heartbeat（roomId/workerId/sessions），失败静默重试；
    entrypoint（:221）里 create_task 启动，进程退出前 cancel。"""
```
2. 后端：
   - `backend/app/services/stt.py` 增模块级 `_HEARTBEATS: dict[str, dict]`（`room_id → {worker_id, last_seen_at, sessions}`）+ `record_heartbeat(room_id, worker_id, sessions)` + `last_heartbeat(room_id) -> dict | None`。
   - `backend/app/api/routers/transcripts.py` 增 `POST /api/stt/heartbeat`（body `{roomId, workerId, sessions}`；鉴权：`X-Agent-Token` = `SESSION_SECRET` 的 HMAC（同一 .env），避免明文；本机回环也不再放宽）。
   - `GET /api/stt/status` 响应增字段：`lastHeartbeatAt`（全局最近一次）——**保持向后兼容**（前端现只读 `mode`）。
   - 新增 `GET /rooms/{room_id}/stt-status`（或给现有 `status` 加可选 `?roomId=`）：返回 `{mode, agentName, maxSessions, agentPresent, lastHeartbeatAt}`，供芯片按房显示。
3. 前端 `frontend/src/hooks/useTranscription.ts` + `DeviceBar.tsx`：芯片判据改为 `agentPresent || (now - lastHeartbeatAt) < 15s`；`title` 增「最后心跳：Xs 前」；worker 停 15 秒后回「未开启」。

备选形态（乙，需迁移 011 新表 `stt_agents`）：多后端进程 / 多机部署时准确；本轮不做（单机演示）。
**待你拍板：取甲（建议）还是乙**（见 §7 Q1）。

## 3. C 组：用例

| 用例 | 文件 | 断言 |
| --- | --- | --- |
| `test_stt_mode_off_skips_upload_and_store` | `backend/tests/test_transcript_segments.py`（紧邻 `test_stt_status_reports_agent_mode` :152） | `monkeypatch` 置 `stt_mode='off'` → 上传/回传返回「未开启」提示、`transcripts` 表 0 行、`stt/status.mode == 'off'` |
| `test_room_full_auto_rejects_pending_requests` | `backend/tests/test_rooms_api.py`（或 `test_room_events_messages.py`） | 在册 = 容量 → 既有 2 条 pending → 新申请 409 后：两条 pending 全变 `rejected`、系统消息含「自动拒绝」、`GET …?status=pending` 为空 |
| `test_approve_when_full_also_auto_rejects` | 同上 | 满员时批准被 409 挡回，但 pending 仍被清理（验证「先提交后抛错」） |

## 4. D 组：人工真机剧本

见 `docs/rounds/r011-debt-backfill/manual-verification.md`（MV-1~MV-9，每项含前置 / 步骤 / 判据 / 回填位 / 预估耗时）。

## 5. 失败与边界

| 场景 | 处理 |
| --- | --- |
| 满员自动拒时数据库并发（两人同时申请） | 房间行锁内批量更新；被拒条数可能为 0（无 pending）→ 不写汇总消息 |
| `approve_join_request` 满员路径抛错与「批量拒绝已提交」的原子性 | 先 `commit` 再 `raise`（拒绝是独立事实，不应被回滚）；`design` 与本页 §2 一致 |
| worker 心跳端点被外部调用 | HMAC（`SESSION_SECRET`）不匹配 → 401；不写内存态 |
| 后端重启 | `_HEARTBEATS` 内存态清空 → 芯片按「无心跳」显示未开启（与现状一致，不伪装） |
| 邀请码页面自动提交 | 只触发一次（`useRef`）；失败仍显示服务端 message，不自动重试 |
| 旧链接（无 `auto=1`） | 行为不变：回填码 + 手动点「加入房间」 |

## 6. 设计变更记录

| 日期 | 级别 | 改了什么 | 依据 |
| --- | --- | --- | --- |
| 2026-09-20 | L2 | 满员时自动拒绝该房待批申请（原为房主点批准才被挡回） | 你 2026-09-20「在等待的自动拒绝」 |
| 2026-09-20 | L1 | 顶栏加「邀请码加入」常驻入口；未登录点「加入房间」跳登录并 `returnTo` 回原码 | 你 2026-09-20 授权原话「r011」（破补正轮纪律） |
| 2026-09-20 | L3 | 新增 `POST /api/stt/heartbeat` + `/rooms/{id}/stt-status` 字段 `lastHeartbeatAt` | 同上 |
| 2026-09-20 | L0 | 文档回填与验收清单回勾（不改行为） | 本轮审计报告 |

## 7. 待拍板

| # | 问题 | 选项 | 建议 |
| --- | --- | --- | --- |
| Q1 | worker 健康上报形态 | ① 内存态 + 心跳端点（零迁移，单机准确）② 新表 `stt_agents`（迁移 011，多进程/多机准确） | ① |
| Q2 | 满员自动拒的通知粒度 | ① 房内一条汇总系统消息 ② 每个被拒申请各一条 ③ 汇总 + 给申请人站内提示（需推送通道，r012 的 SSE 可承接） | ①（本轮）；③ 转 r012 |

## 8. 收工清单（不在本轮执行，开发全部结束后一次做）

1. `python backend/scripts/db_init.py --reset --seed` 还原演示库（去掉历次取证留下的测试房间与 `cp*-*` 账号）——你已定「开发结束后统一清」。
2. `agents.bat` / `dev.bat` 起的进程全部停掉（按端口查监听者）。
3. 交付物两格（AI 工具与模型清单、投入小时数）待你填；部署与演示录屏排 r012 之后。
