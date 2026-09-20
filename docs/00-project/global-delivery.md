---
title: 交付说明（面试作业 · 题目 A：Learning Guide 学习讨论室）
description: 交给评审的交付说明书：题目 A 交付物四项的落点、提交口径与命名、本机起服务与演示路径、设计说明导读、验证证据索引。事实不重抄，一律链到既有页。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-20
rounds: [global]
---

<!-- overview -->
本页是**交付与提交的入口页**：评审按 §1 的 15 分钟路径复核，现场按 §4 的路径复现演示，提交按 §3 的口径打包。
细节不在此重抄（禁双源）：运行说明归 `README.md`，演示流程归 `docs/00-project/demo-runbook.md`，作业逐条对照归 `docs/00-project/assignment-a-coverage.md`。

**交付用 docx 导出件**：仓库根 `交付说明-题目A.docx`（由本页导出，内容同源）。

## 1. 评审 15 分钟复核路径

| 分钟 | 在哪 | 做什么 | 期望看到 |
| --- | --- | --- | --- |
| 0–2 | 仓库根（终端） | `python backend/scripts/db_init.py --seed` | 打印各表行数与演示账号/示例房间 |
| 2–4 | 仓库根 | 双击 `dev.bat` | 后端 `127.0.0.1:8000` 与前端 `localhost:5173` 就绪；自检 `dev.bat check` |
| 4–12 | 浏览器 A / B | 照 `README.md`「两个浏览器演示完整路径」（10 步）或台本 S1~S9 | 注册 → 建房（主题绑定）→ 等候室审批 → 音视频 / 共享 / 举手 / 焦点 / 群聊 → 服务端踢人 → 结束房间 → LLM 纪要 |
| 12–13 | 终端 | `python backend/scripts/smoke.py --base-url http://127.0.0.1:8000` | 末尾打印 `PASS n/n` |
| 13–15 | 本页 §2 / §5 | 交付物四项 + 设计说明导读 | 逐项可点、可跑 |

## 2. 交付物四项（作业《题目 A 交付物》）

| 作业要求 | 落点 |
| --- | --- |
| ① 源代码或 Git 仓库链接 | 本仓（git 仓库；当前工作分支 `req/r013-demo-readiness`，`main` 为已收官轮次的基线） |
| ② 设计说明 + README + 环境变量示例（无真实密钥） | 设计说明 = `docs/01-architecture/`（架构）+ `docs/02-modules/`（模块实现与功能）+ `docs/03-decisions/`（ADR：关键决策与取舍）+ `docs/rounds/`（每轮 design / changes / review）；运行说明 = `README.md`；键名示例 = `.env.example`（只有键名与占位值） |
| ③ 测试或冒烟脚本运行说明 | 命令与最近实测见 §6；脚本 = `backend/scripts/smoke.py`（真实 HTTP 全链路）与 `backend/tests/`（pytest，含 schema 断言、服务层、接口层、真机自检脚本） |
| ④ 使用的 AI 工具与模型列表 | `docs/00-project/ai-tools-and-models.md`（工具、模型，以及实际投入小时数） |

## 3. 提交口径（作业 §四）

| 作业要求 | 本项目口径 |
| --- | --- |
| 文件命名 | `AI管培生_陀梓皓_题目A_<日期>.zip` |
| 注明所选题目与实际投入小时数 | 题目 = **A**；实际投入 ≈ **12 小时**（口径 = 需求与设计文档 + 后端与数据库 + 前端 + 测试与文档回填的合计），填在 `docs/00-project/ai-tools-and-models.md` §3 |
| 使用开源模板须注明来源与新增/修改部分 | **未使用任何前端模板**（自写 React + Vite + 自写样式）；后端 FastAPI 自写；LiveKit 仅用官方 SDK；**未使用 LiveKit Meet 默认页面** |
| 提交形态 | zip + GitHub 仓库链接（+ npm 包），细则见 `docs/00-project/global-roadmap.md` §1「外部归宿与口径」与 `docs/03-decisions/r001-adr-0004-submission-artifacts.md` |

## 4. 本机起服务与演示

前置：本机 PostgreSQL 在跑、库与角色已建（教程 `docs/tutorials/r001-postgres-setup.md`）、conda 环境 `learningguide` 就绪、仓库根 `.env` 已填（键名见 `.env.example`，**值只在本机，不入库**）。

| # | 步骤 | 命令 / 动作 | 判据 |
| --- | --- | --- | --- |
| 1 | 数据库 | `python backend/scripts/db_init.py --seed` | 打印 `schema_migrations 12`（迁移文件 `backend/app/db/sql/001..012`）+ 演示账号与示例房间行数 |
| 2 | 后端 + 前端 | 双击 `dev.bat`（或分别起 uvicorn / `npm run dev`） | 后端 `127.0.0.1:8000`、前端 `localhost:5173`；停止 `dev.bat stop` |
| 3 | 转写 worker（演示语音转写才起） | 双击 `agents.bat` | 窗口出现「`LIVEKIT_URL` 已从 `.env` 注入」+ `registered worker` 两行；零配额联调先 `set AGENT_STT=fake` |
| 4 | 演示 | 照 `docs/00-project/demo-runbook.md` | 6 分 35 秒主流程 + 3 分钟取舍表 + 按钮速查 + 故障兜底 + 录屏分镜 |

- **运行形态**：开发 = `dev.bat` 起本机两个进程（uvicorn + Vite）；交付与演示形态 = 单进程同源（`.env` 的 `APP_ENV=demo` + `npm run build` 后由 uvicorn 托管 `frontend/dist`，只开 8000 一个端口）。评审复现只需 PostgreSQL + conda 环境 + Node。
- **地址口径**：后端一律 `127.0.0.1:8000`（写 `localhost:8000` 每次请求多等约 2 秒）；前端一律 `localhost:5173`（浏览器安全上下文 + Vite 只绑回环）。
- **演示账号（种子）**：`host@example.com`（林泽宇 · 房主）、`mod@example.com`（陈慕 · 协管）、`part@example.com`（王一诺 · 成员）、`admin@example.com`（平台管理员 · 超管）；口令统一 `demo1234`。
- **演示房与素材**：见 `docs/00-project/demo-runbook.md` §0 第 3 项（含一间预铺 10 段对话的纪要演示房）。
- **现场道具**：`demo-window.bat`（受控演示窗口）、`demo-firewall-cut.bat`（防火墙真断 12 秒后自动恢复并删规则，需管理员）、`demo-disconnect.bat`（免管理员备选）、`reconnect-drill.bat`（人工演练回填）。用法与实测数字见 `demo-runbook.md` §3.5 与 `docs/00-requirements/r013-demo-readiness.md` §10.6。

## 5. 设计说明导读（评审按图索骥）

作业「设计说明」各节的逐项对号入座表在 `docs/00-project/assignment-a-coverage.md` §6（唯一一处，本页不重抄）。关键入口：

- **架构 / 权限 / 安全**：`docs/01-architecture/r001-app-architecture.md`（§5 配置与密钥、§13 安全）；实时层增量 `docs/01-architecture/r002-realtime-architecture.md`、`docs/01-architecture/r004-realtime-extras-architecture.md`
- **表结构**：`backend/app/db/sql/001_schema.sql`（手写 SQL 即交付物）+ 模块页 `docs/02-modules/r001-rooms.md`
- **LiveKit 与两个自定义能力（举手 / 焦点）**：`docs/02-modules/r002-livekit{,-features}.md`、`r004-room-extras{,-features}.md`；优先级规则见 ADR-0014、授权见 ADR-0021
- **等候室与踢人流程**：`docs/02-modules/r002-livekit-features.md`（F-17）、ADR-0011
- **纪要生成链路**：`docs/02-modules/r008-assignment-gaps.md` §1、ADR-0018
- **语音转写链路**：`docs/02-modules/r010-transcription.md`、ADR-0023

## 6. 验证证据索引

| 命令 | 最近实测 | 出处 |
| --- | --- | --- |
| `pytest backend/tests -q` | **212 passed**（2026-09-20） | `docs/rounds/r013-demo-readiness/review.md` §E11 |
| `python backend/scripts/smoke.py --base-url http://127.0.0.1:8000` | **PASS 59/59**（2026-09-20 本页定稿时复跑） | 同上 |
| `npx tsc --noEmit --project frontend` + `npm run build` | exit 0（2026-09-20，cp-15 / cp-16 之后复跑） | 同上 |
| 真机自检 5 份（台本 UI / 台本行为流 / 超管隐身 / 三人档焦点 / 强停共享） | 30-30 · 18-18 · 17-17 · 8-8 · 0.5 秒清格 | `docs/rounds/r013-demo-readiness/review.md` §E1 / §E3 / §E9 / §E10 / §E11 |

必做 15 条的逐条实现位置与证据：`docs/00-project/assignment-a-coverage.md` §2。

## 7. 变更记录

| 日期 | 版本 | 改了什么 | 依据 |
| --- | --- | --- | --- |
| 2026-09-20 | v5 | **简化定稿**：只保留交付物落点 / 提交口径 / 起服务与演示 / 设计说明导读 / 证据索引五节；交付物表去掉状态列；运行形态为正向描述（`dev.bat` 两进程 / uvicorn 托管 dist 单进程同源） | 本人 2026-09-20「简化」 |
| 2026-09-20 | v4 | 增「交付用 docx 导出件」说明：仓库根 `交付说明-题目A.docx`（本页导出，同源） | 本人 2026-09-20「交付写一份 docx 到项目根」 |
| 2026-09-20 | v3 | 补部署形态与运行方式说明（本机两进程 / 单进程同源自托管） | 本人 2026-09-20 |
| 2026-09-20 | v2 | 补时间口径：总制作 ≈ 12 小时 | 本人 2026-09-20 |
| 2026-09-20 | v1 | 建页：交付物对照、提交口径、起服务与演示、设计说明导读、验证证据索引 | 本人 2026-09-20「写交付文档（用来交付面试作业，题目一）」 |
