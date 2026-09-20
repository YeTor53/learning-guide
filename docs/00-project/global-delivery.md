---
title: 交付说明（面试作业 · 题目 A：Learning Guide 学习讨论室）
description: 交给评审的交付说明书：正文四节 = 作业《题目 A 交付物》四项（源代码或 Git 仓库链接 · 设计说明+README+环境变量示例 · 测试或冒烟脚本运行说明 · 使用的 AI 工具与模型列表），每节写清「是什么 → 落在哪 → 怎么用/怎么验」；附录 = 评审复核路径、提交口径、变更记录。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-20
rounds: [global]
---

<!-- overview -->
本页是**交付与提交的入口页**。**正文四节 = 作业《题目 A 交付物》四项**，逐项给落点与用法；附录 A 是评审 15 分钟复核路径，附录 B 是提交口径。
细节不在此重抄（禁双源）：运行说明归 `README.md`，演示流程归 `docs/00-project/demo-runbook.md`，作业逐条对照归 `docs/00-project/assignment-a-coverage.md`。

**交付用 docx 导出件**：仓库根 `交付说明-题目A.docx`（由本页导出，内容同源）。

## 1. 源代码或 Git 仓库链接

| 项 | 内容 |
| --- | --- |
| Git 仓库链接 | `https://github.com/YeTor53/learning-guide`（远端 `origin`；`main` = 已收官轮次基线，14 条 `req/rNNN-*` 需求分支同仓可查） |
| 本地工作区 | `G:\VSCODE\VS_items\LearningGuide-LiveKit`（本页所在分支 `req/r013-demo-readiness`，已并入 `main`） |
| 技术栈 | 后端 FastAPI + PostgreSQL（手写 SQL 迁移）+ LiveKit 官方 Server SDK；前端 React + TypeScript + Vite；实时音视频 = LiveKit；语音转写 = LiveKit Agents（房间侧识别）；讨论纪要 = OpenAI 兼容 LLM |
| 交付形态 | zip（命名 `AI管培生_陀梓皓_题目A_<日期>.zip`，见附录 B）+ 上面的仓库链接 |

**怎么把源码跑起来**（前置：本机 PostgreSQL 已建库与角色 —— 教程 `docs/tutorials/r001-postgres-setup.md`；conda 环境 `learningguide`；Node；仓库根 `.env` 按 `.env.example` 键名填好，值只在本机）

| # | 步骤 | 命令 / 动作 | 判据 |
| --- | --- | --- | --- |
| 1 | 数据库 | `python backend/scripts/db_init.py --seed` | 打印 `schema_migrations 12`（迁移文件 `backend/app/db/sql/001..012`）+ 演示账号与示例房间行数 |
| 2 | 后端 + 前端 | 双击 `dev.bat`（或分别起 uvicorn / `npm run dev`） | 后端 `127.0.0.1:8000`、前端 `localhost:5173` 就绪；只自检不启动用 `dev.bat check`，停止用 `dev.bat stop` |
| 3 | 转写 worker（要演示语音转写才起） | 双击 `agents.bat` | 窗口出现「`LIVEKIT_URL` 已从 `.env` 注入」+ `registered worker` 两行才算起好；零配额联调先 `set AGENT_STT=fake` |
| 4 | 演示 | 照 `README.md`「两个浏览器演示完整路径」（10 步）或 `docs/00-project/demo-runbook.md` | 注册 → 建房（主题绑定）→ 等候室审批 → 音视频 / 共享 / 举手 / 焦点 / 群聊 → 服务端踢人 → 结束房间 → LLM 纪要 |

- **运行形态**：开发 = `dev.bat` 起本机两个进程（uvicorn + Vite）；交付与演示形态 = 单进程同源（`.env` 的 `APP_ENV=demo` + `npm run build` 后由 uvicorn 托管 `frontend/dist`，只开 8000 一个端口）。评审复现只需 PostgreSQL + conda 环境 + Node，无需容器。
- **地址口径**：后端一律 `127.0.0.1:8000`（写 `localhost:8000` 每次请求多等约 2 秒）；前端一律 `localhost:5173`（浏览器安全上下文 + Vite 只绑回环）。
- **演示账号（种子）**：`host@example.com`（林泽宇 · 房主）、`mod@example.com`（陈慕 · 协管）、`part@example.com`（王一诺 · 成员）、`admin@example.com`（平台管理员 · 超管）；口令统一 `demo1234`。
- **演示房与素材**：见 `docs/00-project/demo-runbook.md` §0 第 3 项（含一间预铺 10 段对话的纪要演示房）。
- **现场道具**：`demo-window.bat`（受控演示窗口）、`demo-firewall-cut.bat`（防火墙真断 12 秒后自动恢复并删规则，需管理员）、`demo-disconnect.bat`（免管理员备选）、`reconnect-drill.bat`（人工演练回填）。用法与实测数字见 `docs/00-project/demo-runbook.md` §3.5 与 `docs/00-requirements/r013-demo-readiness.md` §10.6。

## 2. 设计说明 + README + 环境变量示例（无真实密钥）

**① 设计说明**（各节内容与落点；作业「设计说明」九节的逐项对号入座表在 `docs/00-project/assignment-a-coverage.md` §6，唯一一处，本页不重抄）

| 内容 | 落点 |
| --- | --- |
| 架构 / 分层 / 安全边界 | `docs/01-architecture/r001-app-architecture.md`（§5 配置与密钥、§13 安全）；实时层增量 `docs/01-architecture/r002-realtime-architecture.md`、`docs/01-architecture/r004-realtime-extras-architecture.md` |
| 表结构 | `backend/app/db/sql/001_schema.sql`（手写 SQL 即交付物）+ 模块页 `docs/02-modules/r001-rooms.md` |
| LiveKit 与两个自定义能力（举手 / 焦点） | `docs/02-modules/r002-livekit{,-features}.md`、`r004-room-extras{,-features}.md`；优先级规则 ADR-0014、授权 ADR-0021 |
| 等候室与踢人流程 | `docs/02-modules/r002-livekit-features.md`（F-17）、ADR-0011 |
| 纪要生成链路 | `docs/02-modules/r008-assignment-gaps.md` §1、ADR-0018 |
| 语音转写链路 | `docs/02-modules/r010-transcription.md`、ADR-0023 |
| 关键决策与取舍（ADR 全量） | `docs/03-decisions/` |
| 每一轮的实现 / 台账 / 审查 | `docs/rounds/rNNN-*/{design,changes,review}.md` |

**② README**：仓库根 `README.md` —— 环境变量、安装、启动命令、两个浏览器演示完整路径（10 步）。

**③ 环境变量示例（无真实密钥）**：仓库根 `.env.example`，只列键名与占位值；真实 `.env` 未入库（`.gitignore` 挡住），仓库跟踪文件中没有真密钥。

| 分组 | 键名 |
| --- | --- |
| 必填 | `DATABASE_URL`、`SESSION_SECRET` |
| 应用 | `APP_ENV`、`CORS_ORIGINS`、`ROOM_CAPACITY`、`INVITE_TTL_MAX_SECONDS` |
| LiveKit（服务端专用，`SECRET` 绝不进前端） | `LIVEKIT_URL`、`LIVEKIT_API_KEY`、`LIVEKIT_API_SECRET`、`LIVEKIT_MODE` |
| 纪要 LLM（OpenAI 兼容） | `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL` |
| 语音转写 | `STT_MODE`、`STT_AGENT_NAME`、`STT_MAX_SESSIONS`（Backend 路径另需 `STT_BASE_URL` / `STT_API_KEY` / `STT_MODEL`） |
| 转写 worker 心跳（可选） | `AGENT_BACKEND_URL`、`AGENT_HEARTBEAT_SECONDS` |
| 在线判定与大屏（r012，可选） | `PRESENCE_ONLINE_SECONDS`、`GLOBAL_CHAT_RATE_LIMIT`、`GLOBAL_CHAT_RATE_WINDOW_SECONDS`、`GLOBAL_CHAT_PAGE`、`SSE_KEEPALIVE_SECONDS`、`SSE_SUBSCRIBER_QUEUE_MAX`、`SSE_MAX_SUBSCRIBERS` |

密钥纪律：`LIVEKIT_API_SECRET` 只允许存在于服务端进程环境变量，前端代码、前端产物、日志、错误响应中都不出现（`docs/01-architecture/r001-app-architecture.md` §5 / §13）。

## 3. 测试或冒烟脚本运行说明

前置：后端已在跑（§1 步骤 2）；命令都在仓库根、conda 环境 `learningguide` 下执行。

| 命令 | 期望输出 | 最近实测 |
| --- | --- | --- |
| `pytest backend/tests -q` | 全绿 | **212 passed**（2026-09-20，出处 `docs/rounds/r013-demo-readiness/review.md` §E11） |
| `python backend/scripts/smoke.py --base-url http://127.0.0.1:8000` | 末尾打印 `PASS n/n`（真实 HTTP 全链路：注册 → 建房 → 申请 → 批准 → 离开 → 结束 + 邀请 / 纪要 / 超管 / 大屏） | **PASS 59/59**（2026-09-20，同上） |
| `npx tsc --noEmit --project frontend` 与 `npm run build` | exit 0 | exit 0（2026-09-20，cp-15 / cp-16 之后复跑） |
| 真机自检脚本 5 套（逐套串行跑，无头 Chrome） | 各脚本末尾 `PASS n/n` | 台本 UI 30-30 · 台本行为流 18-18 · 超管隐身 17-17 · 三人档焦点 8-8 · 强停共享 0.5 秒清格（`docs/rounds/r013-demo-readiness/review.md` §E1 / §E3 / §E9 / §E10 / §E11） |

- **各层在哪**：`backend/tests/` = pytest（schema 断言 + 服务层 + 接口层，外部 LLM/STT 打桩、离线可跑）；`backend/scripts/smoke.py` = 真实 HTTP 冒烟；`frontend/scripts/verify-*.py|mjs` = 真机自检（`frontend/scripts/verify-runbook-ui.py`、`frontend/scripts/verify-runbook-flow.py`、`frontend/scripts/verify-focus-three-way.py`、`frontend/scripts/verify-screen-force-stop.py`、`backend/scripts/verify_r012_superadmin_invisible.py`）。
- **必做 15 条的逐条实现位置与证据**：`docs/00-project/assignment-a-coverage.md` §2。

## 4. 使用的 AI 工具与模型列表

**① 编程 / 研究工具**

| 工具 | 用在哪 |
| --- | --- |
| Hermes Agent（本仓开发代理，代理模型 `deepseek-v4-flash`） | 需求梳理、设计文档、前后端实现、用例与真机验证（Playwright / CDP），全程留痕在 git 提交与 `docs/` |

**② 产品运行时用到的模型 / 服务**

| 用途 | 模型 / 服务 |
| --- | --- |
| 讨论纪要生成（产品功能） | `LLM_MODEL`（当前指向 DeepSeek `deepseek-chat`），OpenAI 兼容接口 |
| 语音转文字（r010） | 主路径 = 房间侧识别：LiveKit Agents worker + LiveKit Inference（免自备 key）；备用路径 = 云端 Whisper 兼容 REST（`STT_MODE=backend`）/ 本地 faster-whisper（离线兜底） |
| 实时音视频 | LiveKit（云项目） |

完整清单与口径（含实际投入小时数 ≈ 12 小时、开源模板声明、运行形态声明）在 `docs/00-project/ai-tools-and-models.md`。

## 附录 A 评审 15 分钟复核路径

| 分钟 | 在哪 | 做什么 | 期望看到 |
| --- | --- | --- | --- |
| 0–2 | 仓库根（终端） | `python backend/scripts/db_init.py --seed` | 打印各表行数与演示账号 / 示例房间（幂等补种；不要用 `--reset`，见附录 B 末注） |
| 2–4 | 仓库根 | 双击 `dev.bat` | 后端 `127.0.0.1:8000` 与前端 `localhost:5173` 就绪；自检 `dev.bat check` |
| 4–12 | 浏览器 A / B | 照 `README.md`「两个浏览器演示完整路径」（10 步）或台本 S1~S9 | 注册 → 建房（主题绑定）→ 等候室审批 → 音视频 / 共享 / 举手 / 焦点 / 群聊 → 服务端踢人 → 结束房间 → LLM 纪要 |
| 12–13 | 终端 | `python backend/scripts/smoke.py --base-url http://127.0.0.1:8000` | 末尾打印 `PASS n/n` |
| 13–15 | 本页 §2 / §4 | 设计说明导读 + AI 工具与模型列表 | 逐项可点、可跑 |

## 附录 B 提交口径（作业 §四）

| 作业要求 | 本项目口径 |
| --- | --- |
| 文件命名 | `AI管培生_陀梓皓_题目A_<日期>.zip` |
| 注明所选题目与实际投入小时数 | 题目 = **A**；实际投入 ≈ **12 小时**（口径 = 需求与设计文档 + 后端与数据库 + 前端 + 测试与文档回填的合计），填在 `docs/00-project/ai-tools-and-models.md` §3 |
| 使用开源模板须注明来源与新增/修改部分 | **未使用任何前端模板**（自写 React + Vite + 自写样式）；后端 FastAPI 自写；LiveKit 仅用官方 SDK；**未使用 LiveKit Meet 默认页面** |
| 提交形态 | zip + Git 仓库链接（`https://github.com/YeTor53/learning-guide`） |

注：准备演示不要用 `db_init.py --reset --seed`（会清掉手工建的演示房）；用 `python backend/scripts/clean_demo_junk.py --yes` 只清测试垃圾。

## 附录 C 变更记录

| 日期 | 版本 | 改了什么 | 依据 |
| --- | --- | --- | --- |
| 2026-09-20 | v6 | **正文改为作业交付物四项**：§1 源代码或 Git 仓库链接（并入原「本机起服务与演示」）、§2 设计说明 + README + 环境变量示例（并入原「设计说明导读」，并补 `.env.example` 键名分组表）、§3 测试或冒烟脚本运行说明（并入原「验证证据索引」）、§4 使用的 AI 工具与模型列表；原「评审 15 分钟复核路径」与「提交口径」降为附录 A / B；Git 仓库链接落定为 `https://github.com/YeTor53/learning-guide` | 本人 2026-09-20「将交付说明主要内容改为四项」 |
| 2026-09-20 | v5 | **简化定稿**：只保留交付物落点 / 提交口径 / 起服务与演示 / 设计说明导读 / 证据索引五节；交付物表去掉状态列；运行形态为正向描述（`dev.bat` 两进程 / uvicorn 托管 dist 单进程同源） | 本人 2026-09-20「简化」 |
| 2026-09-20 | v4 | 增「交付用 docx 导出件」说明：仓库根 `交付说明-题目A.docx`（本页导出，同源） | 本人 2026-09-20「交付写一份 docx 到项目根」 |
| 2026-09-20 | v3 | 补部署形态与运行方式说明（本机两进程 / 单进程同源自托管） | 本人 2026-09-20 |
| 2026-09-20 | v2 | 补时间口径：总制作 ≈ 12 小时 | 本人 2026-09-20 |
| 2026-09-20 | v1 | 建页：交付物对照、提交口径、起服务与演示、设计说明导读、验证证据索引 | 本人 2026-09-20「写交付文档（用来交付面试作业，题目一）」 |
