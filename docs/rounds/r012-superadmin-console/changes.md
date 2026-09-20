---
title: r012 变更台账（cp 逐格记录）
description: r012（超管 · 管理后台 · 全服大屏聊天）的提交台账、门禁数字、用户消息回执台账与实测留痕位；cp-1 建骨架，逐 cp 追加。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-20
---

<!-- overview -->
本页与实现**同提交**逐行追加（AGENTS.md 硬规矩 6：文档与代码同一次提交）。cp-1 建骨架，此后每个 cp 追加一行并填门禁数字。
分支 `req/r012-superadmin-console`；基点 = `req/r011-debt-backfill` @ `ab8edb5`（cp-7）。tag 逐个 cp 打 `cp-r012-N`。

## 1. cp 台账

| cp | 提交 | 内容 | 门禁数字（pytest / smoke / tsc+build） | 依据 |
| --- | --- | --- | --- | --- |
| cp-r012-1 | 本次提交 | 阶段 1 文档：需求单 + design + changes/review 骨架 + 轮次索引行 + `redirect-01` 指针 | 不适用（纯文档，未跑门禁；代码门禁从 cp-2 起） | 需求单 §9 |
| cp-r012-1b | 本次提交 | 阶段 1 批复登记：Q1~Q18 落地（需求单 §10.1）+ 按批改写 design（只管理不发布音视频 / 右侧 Copilot 式面板 / 前端短轮询心跳）+ 把 r011 收尾提交 `cp-8`/`cp-8b` merge 进本分支（`e0c6598`） | 不适用（纯文档） | 需求单 §10.1 |
| cp-r012-2 | 本次提交 | 迁移 011（身份/旁路/大屏/审计五对象）+ 012（演示超管）+ 身份（`users.role` + `UserVO.role` + `roles.py`）+ 在线心跳（`POST /api/presence` + `presence.py` + `usePresenceBeat` + `PRESENCE_ONLINE_SECONDS`）+ 提权脚本 `grant_superadmin.py` + ADR-0024 + 模块实现页首版 | pytest **174 passed**（+10）/ smoke 未跑（本轮 cp-7 统一跑）/ `tsc --noEmit` exit 0 | E1/E14 |
| cp-r012-3 | | 超管隐身进房（hidden Token + `room_visits` + 旁路校验收敛）+ 用例 | | E2/E3/E4/E10 |
| cp-r012-3 | 本次提交 | 超管隐身进房与旁路治理：`issue_token(hidden/attributes/can_publish*)`、`room_visits` 读写、`assert_room_role`/`assert_manager_role` 两处旁路、`effective_role`、离开/结束收口、worker 跳过超管、用例 8 条 | pytest **182 passed** / tsc 未跑（本轮未动前端） | E2/E3/E4/E10/E13（后端侧） |
| cp-r012-4 | | 管理后台后端（三列表 + 三动作 + 审计）+ 用例 | | E5/E6 |
| cp-r012-4 | 本次提交 | 管理后台后端：`repositories/admin.py` + `services/admin.py` + `schemas/admin.py` + `routers/admin.py` + `deps.current_superadmin` + 三列表/三动作/审计 + 用例 9 条 | pytest **191 passed** / tsc 未跑（未动前端） | E5/E6 |
| cp-r012-5 | | 大屏聊天 + SSE 后端 + 限流 + ADR-0025 + 用例 | | E7/E8 |
| cp-r012-6 | | 前端 `/admin` + 大屏面板 + 入口 + 超管视角 + 视觉参数区 + 教学两页 + 模块功能页 | | E5/E9/E12 |
| cp-r012-7 | | 门禁复跑 + 真机取证 + 视觉对账 + 文档回填 + review 定稿 | | E11/E12 |

## 2. 用户消息台账（vibecoding 8.1 判据：每条用户消息一行回执）

| # | 用户原话摘要 | 回执分类 | 单号 | 处置 |
| --- | --- | --- | --- | --- |
| 1 | 「设计LearnGuide项目的r012」 | 新轮次设计请求（沿用已登记 `redirect-01`） | — | 出阶段 1 文档（cp-1）+ `ASK-r012-1` 待批 |
| 2 | 「1 1 1 1 1 1 1 1（…超管不能说话和视频，只能管理！） 1 1 2（右侧的侧栏打开窗口，像编译器里的 coplit） 2（只 admin 可见） 1 2（短轮询） 1 1 1 1」 | 澄清回答（W2，答 `ASK-r012-1` 全 18 项） | — | 批复落需求单 §10.1 + 按批改 design（cp-1b）；两条口径补充记入 Q4/Q8 行 |

## 3. 实测数字与留痕（逐 cp 追加，禁占位）

| 项 | 命令 / 做法 | 实测 | 时间 |
| --- | --- | --- | --- |
| 阶段 1 文档落盘 | `ls docs/rounds/r012-superadmin-console` | 4 个文件：`design.md` / `changes.md` / `review.md` / `redirect-01.md`（+ 需求单 1 个）；cp-1 `0192e25`、cp-1b（本次） | 2026-09-20 |
| 迁移应用 | `python backend/scripts/db_init.py --seed`（**不 reset**，沿用 r011 口径「演示库开发结束后统一清」） | `[migrate] 本次应用版本：011_r012_superadmin_global_chat, 012_r012_seed_superadmin`；`schema_migrations 12`；新表 `room_visits / global_messages / admin_audit` 各 0 行 | 2026-09-20 |
| 演示超管 | `db_init.py --seed` 后查库 | `usr_demo_admin / admin@example.com / 平台管理员 / role=superadmin`（last_seen_at 初始 NULL） | 2026-09-20 |
| 提权脚本 | `python backend/scripts/grant_superadmin.py --email host@example.com` → `--revoke`；再试不存在的邮箱 | `user → superadmin（影响 1 行；id=usr_demo_host）` / `superadmin → user（影响 1 行；id=usr_demo_host）` / 退出码 2 `找不到账号：nobody@example.com` | 2026-09-20 |
| 用例（cp-2） | `pytest backend/tests -q` | **174 passed**（r011 基线 164；新增 10 条：`test_presence_api.py` 4 + `test_superadmin_identity.py` 6）42.83s | 2026-09-20 |
| 用例（cp-3） | `pytest backend/tests -q` | **182 passed**（新增 8 条：`test_superadmin_room_access.py`）45.03s | 2026-09-20 |
| 用例（cp-4） | `pytest backend/tests -q` | **191 passed**（新增 9 条：`test_admin_api.py`）48.57s | 2026-09-20 |
| 鉴权矩阵 | 用例：房主与游客打四读三写 | 四读 403 / 三写 403 / 未登录清理 Cookie 后 401 | 2026-09-20 |
| 删房 | 用例：删前插一条消息，删后查库 | `{deleted: true, livekitApplied: true}`（LiveKit 打桩）；`rooms` 行消失、`get /api/rooms/{id}` 404、该房 `chat_messages` 计数 0、审计里 `detail.snapshot.title/messageCount` 仍在 | 2026-09-20 |
| 超管 Token claims | 用例解 JWT 断言 | `hidden=True` / `canPublish=False` / `canPublishData=False` / `roomAdmin` 非真 / `attributes={'lg-role':'superadmin'}` / `maxParticipants=房间容量` | 2026-09-20 |
| 满员房 | 用例：房主 + 7 成员（在册 8） | 超管取票 200 且 `memberCount` 恒 8；路人 403 `NOT_MEMBER` | 2026-09-20 |
| 前端类型 | `cd frontend && npx tsc --noEmit` | exit 0 | 2026-09-20 |
| 前端构建 | `cd frontend && npm run build` | exit 0（`tsc --noEmit && vite build`；2011 modules，`dist/assets/index-DB_GFgTm.js` 962.81 kB / gzip 272.75 kB） | 2026-09-20 |
| 密钥扫描 | `git grep -nE "API_SECRET|API_KEY" -- backend/app frontend/src` | 命中 8 行，**全部为键名/变量名**（`config.py` 6 处变量名 + `stt.py:82`、`summary.py:103` 报错文案 + `RoomSummaryPage.tsx:96` 提示文案），**本轮新增命中 0**、无任何密钥值 | 2026-09-20 |
| 未新增依赖 | `git diff --stat -- frontend/package.json backend/requirements*.txt` | 空 | 2026-09-20 |
| 门禁四项 | `pytest backend/tests -q` / `smoke.py` / `tsc --noEmit` / `npm run build` | 待填（cp-7；基线 r011：pytest 164 / smoke 47-47 / tsc·build exit 0） | |
| 隐身真机 | 2 浏览器：成员列表 / 舞台 / 人数 | 待填（cp-3） | |
| SSE 真机 | `curl -N http://127.0.0.1:8000/api/events` + 另一客户端发大屏消息 | 待填（cp-5） | |

## 4. 变更记录

| 日期 | 版本 | 改了什么 | 依据 |
| --- | --- | --- | --- |
| 2026-09-20 | 骨架（cp-1） | 建页：cp 台账骨架 + 用户消息台账 + 实测留痕位 | 需求单 §9；vibecoding 8.1 判据 |
| 2026-09-20 | cp-1b | 登记阶段 1 批复（Q1~Q18）与两条补充口径；cp 台账加 cp-1b 行、台账加用户消息 #2；并入 r011 `cp-8`/`cp-8b` | 用户 2026-09-20 批复 |
| 2026-09-20 | cp-2 | 迁移 011/012 + 身份 + 在线心跳 + 提权脚本 + ADR-0024 + 模块实现页首版；用例 174 passed、tsc 0；`roles.py`「角色判据唯一入口」随本 cp 提前落地（提权脚本要用，属 cp-3 计划的同一模块） | 需求单 §9 cp-2、§10.1（Q1/Q14/Q15）；ADR-0024 |
| 2026-09-20 | cp-3 | 超管隐身进房（hidden/只读 Token + `room_visits`）+ 两处旁路收敛 + `effective_role` + worker 跳过超管；用例 182 passed | 需求单 §9 cp-3、§10.1（Q2/Q3/Q4/Q8）、ADR-0024 D2~D5 |
| 2026-09-20 | cp-4 | 管理后台后端（三列表 + 三动作 + 审计 + 鉴权依赖）；用例 191 passed；查询参数定 snake_case（与既有 `mine=` 同口径，design §3.3 同步修正） | 需求单 §9 cp-4、§10.1（Q5/Q6/Q7/Q16）、ADR-0024 D6 |
| 2026-09-20 | cp-4b | **补交**：`services/presence.py::online_since()`——cp-4 提交时漏登记该文件，导致 `GET /api/admin/users?online_only=1` 在 cp-4 树里引用了不存在的函数（本地工作区有、提交里没有）。教训记在此：**冷启动核对**（提交后 `git status` 必须为空，本轮 cp-4 曾遗留一个未登记的已改文件） | cp-4 自审发现 |
