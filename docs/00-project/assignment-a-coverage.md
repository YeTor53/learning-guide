---
title: 面试作业「题目 A」覆盖情况（对照 G:\Downloads\设计-r003-api接入.docx）
description: 逐条核对作业必做/加分/交付物与仓库现状，附证据指路、缺口与建议下一步（2026-09-20 r011 重写去重、数字实测更新）。
type: reference
status: proposed
owner: 陀梓皓
updated: 2026-09-20
---

<!-- overview -->
作业原文：`G:\Downloads\设计-r003-api接入.docx`（题目 A = Learning Guide 学习讨论室 / LiveKit Mini-Product；时限 4 天 ≈16 小时）。本页只做**对照与指路**，不改规范。
本版由 r011 cp-2 **整页重写**（去重：旧版页内出现两组 §5/§6、§7 与 §3 重复；数字更新到 2026-09-20 实测）。

## 1. 结论（2026-09-20 重核）

- **必做：15 / 15 完成**（README 一条原判「内容在但状态与数字过期」，已由 r011 cp-2 补齐 → 改为完成）。
- **加分：0 / 5 全绿**，其中 2 项为「部分」、3 项「未做」且**已排期**：断线重连（部分，等人工演练 MV-1）、录制/旁路转写（转写已完成、**录制经 owner 决定不做**）、Docker Compose/公网部署（排 r012 之后）、简单管理后台（排 r012）、演示录屏（排 r012 之后）。
- **交付物：3 / 4 齐**；缺「使用的 AI 工具与模型列表」中的两格（工具行、投入小时数），**待 owner 填**（模板已建）。
- 产品约束 4 条全部满足：主题绑定（14 主题预设含题目点名的哲学 / 数理生物学 / 德国史）、8 人上限、等候室审批、三种角色。

## 2. 必做逐条（15 条）

| # | 作业要求 | 状态 | 证据 |
| --- | --- | --- | --- |
| 1 | 注册 / 登录 / 登出；未登录不可创建或加入房间 | **完成** | `backend/app/api/routers/auth.py:27/36/45`（register/login/logout）；前端 `pages/LoginPage.tsx`、`RegisterPage.tsx`、`SideBar.tsx:95`（登出）；未登录走 `require_login` → 401 |
| 2 | 房间：创建（主题/标题/简介）、列表、详情、加入申请、批准/拒绝、离开、结束 | **完成** | `services/rooms.py`（`create_room` :231 / `request_join` :350 / `approve_join_request` :406 / `reject_join_request` :440 / `leave_room` :460 / `end_room` :474）；`smoke` 46/46 |
| 3 | **邀请：可生成限时邀请链接或房间码（需过期时间）** | **完成** | `services/invites.py` + `routers/invites.py:23/37/48`；有效期上限 60 秒（`INVITE_TTL_MAX_SECONDS`）、6 位码、幂等、满员仍 409；前端抽屉「邀请」tab + `/join` 页。**界面入口的缺口（只有链接能到）在 r011 cp-4 补顶栏入口 + 未登录 `returnTo`** |
| 4 | LiveKit：加入、麦克风/摄像头、参与者视频、参与者列表、离开；服务端签发 Token；Secret 不入前端 | **完成** | `services/livekit.py`（`issue_token`、`remove_participant` :89）；前端 `components/live/DeviceBar.tsx:159`（摄像头开关）、`LiveStage.tsx:100`（相机/共享轨渲染）、`useLocalDeviceState.ts:31`；`.env` 未入库、前端只拿短期 token |
| 5 | 屏幕共享；共享时共享画面为主区域，停止后恢复 | **完成** | `hooks/useScreenShare.ts`；`stageLayout`/`stageGeometry` + ADR-0014（共享 > 手动焦点 > 说话者 > 自己） |
| 6 | 文字群聊：实时收发 + 持久化 + 按房间拉最近消息 | **完成** | `routers/room_extras.py:35`（POST 消息）、`:46`（GET 最近消息，`limit` 1~100）；`chat_messages` 表 + DataChannel `lg.chat` 加速、HTTP 落库为唯一真相（ADR-0013） |
| 7 | 自定义能力 1 — 举手：实时同步 + 列表展示 + 协管/房主可「放下」他人举手 | **完成** | `services/hands.py`（含 `lower_hand` by other）；`room_extras.py:61/71/81`；抽屉成员列表可见 ✋ |
| 8 | 自定义能力 2 — 焦点发言：指定焦点、画面放大、取消恢复、与共享并存的优先级规则 | **完成** | `services/focus.py`、`focus_requests`（迁移 008）、ADR-0021（布局与授权）+ ADR-0014（优先级） |
| 9 | 服务端管控：通过 Server API 踢人（不可只做前端假踢） | **完成** | `livekit.py:89` `remove_participant` + `rooms.py:562`（`_safe_livekit` 包裹，失败不回滚、`livekit_applied` 如实标记） |
| 10 | 会后产出：结束后自动/一键生成讨论纪要（LLM）落库 + 详情页可查看；输入至少含聊天记录 | **完成** | 迁移 `007_r008_session_summaries` + `services/summary.py`（唯一 LLM 出口；素材含聊天 + 成员 + 主题 + **语音转写**，见 `summary.py:144-158`）+ `/rooms/{id}/summary` + 纪要页；真机 6.0 秒 / 632 字 |
| 11 | 数据层：可运行 Schema + 迁移/初始化；至少含 users / rooms / room_members / join_requests / chat_messages / session_summaries | **完成** | `backend/app/db/sql/`：`001_schema.sql`（六表齐）+ 迁移到 `010`（共 10 个版本）；`db_init.py` 可重置初始化 |
| 12 | 种子数据：一键写入演示账号、示例房间与历史消息 | **完成** | `002_seed.sql` + `python backend/scripts/db_init.py --reset --seed`（3 演示账号 / 房间 / 历史消息） |
| 13 | 基础自动化验证（≥1 可运行 API/集成测试或脚本化冒烟） | **完成** | `pytest backend/tests -q` → **156 passed**、`smoke.py` → **PASS 46/46**（2026-09-20 实测，见 `docs/rounds/r010-transcription/review.md` §5b） |
| 14 | 设计说明：架构 / 权限矩阵 / 表结构 / LiveKit 与两个自定义能力 / 等候室与踢人 / 纪要链路 / 失败与边界 / 安全 / 未完成项 | **完成** | 见 §5 对照表（架构页、模块页、ADR、各轮 design 的失败与边界、各轮 review 的未闭合项） |
| 15 | README：环境变量 / 安装 / 启动 / 如何用两个浏览器演示完整路径 | **完成**（2026-09-20 补齐） | `README.md`「怎么跑」+「两个浏览器演示完整路径（10 步）」；状态段与数字已更新（`schema_migrations 10` / `pytest 156`）；`.env.example` 含 `LIVEKIT_*` / `LLM_*` / `STT_*` / `INVITE_TTL_MAX_SECONDS` |

## 3. 加分项（5 项）

| 加分项 | 状态 | 说明 |
| --- | --- | --- |
| 断线重连后举手/焦点状态恢复 | **部分** | 状态落库 + DataChannel 名册广播 + 重连/聚焦刷新 + 30 秒兜底；**本地真断演练（E18b/E18c）未做** → 由人工剧本 MV-1 覆盖（`docs/rounds/r011-debt-backfill/manual-verification.md`） |
| 房间录制或旁路录音转写后再生成纪要 | **部分（录制经 owner 决定不做）** | 转写链路已完成（r010：房间侧识别 → 文字并入讨论流 → 进纪要素材；cp-6 离线回归有音频路径硬数字）；**录制/旁路录音不做**（2026-09-20 owner 口径） |
| Docker Compose 一键启动或公网部署 | **未做** | 现为本机 `dev.bat`；**已排期：r012 收工之后** |
| 简单管理后台（房间 / 用户 / 纪要列表） | **未做** | **已排期：并入 r012**（与超管用户同一轮，见 `docs/rounds/r012-superadmin-console/redirect-01.md`） |
| 演示录屏 3–5 分钟 | **未做** | 需人录；**已排期：r012 收工之后** |

## 4. 交付物（4 项）

| 交付物 | 状态 |
| --- | --- |
| 源代码 / Git 仓库链接 | **齐**（本仓；`dev.bat` 一键起 8000 + 5173） |
| 设计说明 + README + 环境变量示例（无真实密钥） | **齐**（`.env` 未入库、`.env.example` 只有键名） |
| 测试或冒烟脚本运行说明 | **齐**（README §⑤ + `backend/scripts/smoke.py`） |
| 使用的 AI 工具与模型列表 | **缺两格，待你填**：`docs/00-project/ai-tools-and-models.md`（§1 工具行「请补」、§3 「实际投入小时数 = 请填」） |

## 5. 提交方式（作业 §四）

| 要求 | 状态 |
| --- | --- |
| 文件命名 `AI管培生_姓名_题目A_日期.zip` | 待打包（P11 里的 zip 口径暂缓） |
| 注明所选题目与实际投入小时数 | 题目 = A（已写）；**小时数待你填**（`ai-tools-and-models.md` §3） |
| 如使用开源模板，注明来源并说明新增/修改部分 | **已声明**：未使用前端模板（自写 React + Vite + 自写样式）、后端 FastAPI 自写、LiveKit 仅用官方 SDK、**未使用 LiveKit Meet 默认页面**（`ai-tools-and-models.md` §3；AGENTS.md 禁区同口径） |

## 6. 设计说明对照表（作业要求 ↔ 本仓文档）

| 作业要求的章节 | 本仓对应文档 |
| --- | --- |
| 架构 | `docs/01-architecture/r001-app-architecture.md`（分层、路由、错误信封、安全边界） |
| 权限矩阵 | `docs/02-modules/r002-livekit-features.md` + `docs/rounds/r004-room-extras/design.md`（三角色 × 动作） |
| 表结构 | `docs/02-modules/r001-rooms.md`（DDL）+ 各轮实现页（004/005/006/007/008/009/010） |
| LiveKit 与两个自定义能力（举手 / 焦点） | `docs/02-modules/r002-livekit.md`、`r004-room-extras.md`、ADR-0014、ADR-0021 |
| 等候室与踢人流程 | `docs/02-modules/r002-livekit-features.md`（F-17）、ADR-0011（Token 无状态 / 外部调用在提交后） |
| 纪要生成链路 | `docs/02-modules/r008-assignment-gaps.md` §1、ADR-0018、`docs/rounds/r008-assignment-gaps/design.md` §2.5 |
| 转写链路（r010 追加） | `docs/02-modules/r010-transcription.md`、ADR-0023、`docs/rounds/r010-transcription/review.md` |
| 失败与边界情况 | 各轮 design 的「失败与边界」表 + 各轮 review 的「未闭合项」+ `docs/rounds/r011-debt-backfill/manual-verification.md` |
| 安全 | `docs/01-architecture/r001-app-architecture.md` §5/§13（密钥只在本机 `.env`、Secret 不进前端、错误不回显内部细节） |
| 未完成项 | 各轮 review「未闭合项」+ `docs/00-requirements/r011-debt-backfill.md`（本轮还账）+ 本页 §3 |

## 7. 建议下一步（2026-09-20）

| 优先级 | 内容 | 为什么 |
| --- | --- | --- |
| P0 | 提交前跑一次人工剧本 MV-1~MV-9（`docs/rounds/r011-debt-backfill/manual-verification.md`） | 验证纪律要求「人工项没有留痕就标未取证」；MV 表就是留痕位 |
| P0 | 填 `ai-tools-and-models.md` 两格 | 4 项交付物里唯一缺口 |
| P1 | r012：超管 + 简单管理后台 + 全服大屏聊天 | 加分项里最像「产品」的一项，且你已点名 |
| P2 | 部署（Docker Compose / 公网）与演示录屏 | 排 r012 之后 |

## 8. 变更记录

| 日期 | 版本 | 改了什么 | 依据 |
| --- | --- | --- | --- |
| 2026-09-19 | v1 | 建页：按作业原文逐条核对必做/加分/交付物，标注缺口与建议排序 | owner 要求「看一遍 docx 确认题目一完成度」 |
| 2026-09-20 | v2（r011 cp-2） | **整页重写去重**（旧版有两组 §5/§6、§7 与 §3 重复）；数字更新为实测（pytest 156 / smoke 46-46 / 迁移 10 / 主题 14）；必做 README 一条补齐后改判完成；加分项五项状态与排期重列；新增 §5 提交方式与 §6 对照表逐项证据 | 2026-09-20「全面检查缺漏项」（题目面 + 需求面）+ r011 本轮 |
