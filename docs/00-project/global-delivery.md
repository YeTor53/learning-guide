---
title: 交付说明（面试作业 · 题目 A：Learning Guide 学习讨论室）
description: 交给评审的交付说明书：题目 A 交付物四项的落点与状态、提交口径（命名 / 题目与小时数 / 开源模板声明）、本机起服务与演示路径、设计说明导读、验证证据索引、已知边界与提交前 checklist。事实不重抄，一律链到既有页。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-20
rounds: [global]
---

<!-- overview -->
本页是**交付与提交的入口页**：评审按 §0 的 15 分钟路径复核，现场按 §3 的路径复现演示，提交按 §2 与 §7 勾选。
细节不在此重抄（禁双源）：运行说明归 `README.md`，演示流程归 `docs/00-project/demo-runbook.md`，作业逐条对照归 `docs/00-project/assignment-a-coverage.md`。

## 0. 评审 15 分钟复核路径

| 分钟 | 在哪 | 做什么 | 期望看到 |
| --- | --- | --- | --- |
| 0–2 | 仓库根（终端） | `python backend/scripts/db_init.py --seed` | 打印各表行数与演示账号/示例房间（幂等补种；**不要**用 `--reset`，见 §3 末注） |
| 2–4 | 仓库根 | 双击 `dev.bat` | 后端 `127.0.0.1:8000` 与前端 `localhost:5173` 就绪；自检 `dev.bat check` |
| 4–12 | 浏览器 A / B | 照 `README.md`「两个浏览器演示完整路径」（10 步）或台本 S1~S9 | 注册 → 建房（主题绑定）→ 等候室审批 → 音视频 / 共享 / 举手 / 焦点 / 群聊 → 服务端踢人 → 结束房间 → LLM 纪要 |
| 12–13 | 终端 | `python backend/scripts/smoke.py --base-url http://127.0.0.1:8000` | 末尾打印 `PASS n/n` |
| 13–15 | 本页 §1 / §4 | 交付物四项对照 + 设计说明导读 | 逐项可点、可跑 |

## 1. 交付物四项（作业《题目 A 交付物》）

| # | 作业要求 | 落点 | 状态 |
| --- | --- | --- | --- |
| ① | 源代码或 Git 仓库链接 | 本仓（本地 git 仓库，14 个需求分支 + `main`；当前工作分支 `req/r013-demo-readiness`）。**远端尚未创建**，见 §7 | 本地齐；GitHub 链接待建 |
| ② | 设计说明 + README + 环境变量示例（无真实密钥） | 设计说明 = `docs/01-architecture/`（架构）+ `docs/02-modules/`（模块实现与功能）+ `docs/03-decisions/`（ADR：关键决策与取舍）+ `docs/rounds/`（每轮 design / changes / review）；运行说明 = `README.md`；键名示例 = `.env.example`（只有键名与占位值） | 齐 |
| ③ | 测试或冒烟脚本运行说明 | 命令与最近实测见 §5；脚本 = `backend/scripts/smoke.py`（真实 HTTP 全链路）与 `backend/tests/`（pytest，含 schema / 服务层 / 接口层 / 真机自检脚本） | 齐 |
| ④ | 使用的 AI 工具与模型列表 | `docs/00-project/ai-tools-and-models.md` | **投入小时数已填（约 12 小时，§3）**；§1 「除 Hermes Agent 外的其它工具」一行待确认（没用别的就写「无其它」） |

## 2. 提交口径（作业 §四）

| 作业要求 | 本项目口径 |
| --- | --- |
| 文件命名 | `AI管培生_陀梓皓_题目A_<日期>.zip` |
| 注明所选题目与实际投入小时数 | 题目 = **A**；**实际投入 ≈ 12 小时**（本人 2026-09-20 确认口径，见 §2.1）；小时数填在 `docs/00-project/ai-tools-and-models.md` §3（**唯一一处**，不在别处重复） |
| 使用开源模板须注明来源与新增/修改部分 | **未使用任何前端模板**（自写 React + Vite + 自写样式）；后端 FastAPI 自写；LiveKit 仅用官方 SDK；**未使用 LiveKit Meet 默认页面**（同 `docs/00-project/ai-tools-and-models.md` §3） |
| 提交形态 | zip + GitHub 仓库链接（+ npm 包），细则 P11 未拍板 → `docs/00-project/global-roadmap.md` §1「外部归宿与口径」、`docs/03-decisions/r001-adr-0004-submission-artifacts.md` |

### 2.1 时间投入与取舍（面试会追问，先写在这里）

- **总制作时间 ≈ 12 小时**（4 个自然日窗口内的实际专注投入；口径 = 需求与设计文档 + 后端与数据库 + 前端 + 测试与文档回填的合计）。若面试要分项细目，可按本仓 git 提交时间线逐条核算。
- **演示录屏（加分⑤）没做：时间来不及。** 完整版 6.5 分钟分镜、按钮逐条脚本、兜底话术、现场道具都已备好（`docs/00-project/demo-runbook.md` §5「录屏分镜」），缺的只是录制与剪辑那一段单独时间；演示本身可直接现场跑（§3）。
- **录制功能（加分②后半）**：转写链路已完成，**录制是主动取舍不做**（同 `assignment-a-coverage.md` §3）。
- **Docker Compose / 公网部署（加分③）**：未做，本机 `dev.bat` 起服务已足够评审复现。
- 三项取舍都**不影响必做 15 条闭环**：必做项 15/15 完成，逐条实现位置与证据见 `docs/00-project/assignment-a-coverage.md` §2。

## 3. 本机起服务与演示

前置：本机 PostgreSQL 在跑、库与角色已建（教程 `docs/tutorials/r001-postgres-setup.md`）、conda 环境 `learningguide` 就绪、仓库根 `.env` 已填（键名见 `.env.example`，**值只在本机，不入库**）。

| # | 步骤 | 命令 / 动作 | 判据 |
| --- | --- | --- | --- |
| 1 | 数据库 | `python backend/scripts/db_init.py --seed` | 打印 `schema_migrations 12`（迁移文件 `backend/app/db/sql/001..012`）+ 演示账号与示例房间行数 |
| 2 | 后端 + 前端 | 双击 `dev.bat`（或分别起 uvicorn / `npm run dev`） | 后端 `127.0.0.1:8000`、前端 `localhost:5173`；停止 `dev.bat stop` |
| 3 | 转写 worker（要演示语音转写才起） | 双击 `agents.bat` | 窗口里出现「`LIVEKIT_URL` 已从 `.env` 注入」+ `registered worker` 两行才算起好；零配额联调先 `set AGENT_STT=fake` 再起 |
| 4 | 演示 | 照 `docs/00-project/demo-runbook.md` | 6 分 35 秒主流程 + 3 分钟取舍表 + 按钮速查 + 故障兜底 + 录屏分镜 |

- **地址口径**：后端一律 `127.0.0.1:8000`（写 `localhost:8000` 每次请求多等约 2 秒）；前端一律 `localhost:5173`（浏览器安全上下文 + Vite 只绑回环）。
- **演示账号（种子）**：`host@example.com`（林泽宇 · 房主）、`mod@example.com`（陈慕 · 协管）、`part@example.com`（王一诺 · 成员）、`admin@example.com`（平台管理员 · 超管）；口令统一 `demo1234`。
- **演示房与素材**：见 `docs/00-project/demo-runbook.md` §0 第 3 项（含一间预铺 10 段对话的纪要演示房，房间码见该行末）。
- **现场道具**：`demo-window.bat`（受控演示窗口）、`demo-firewall-cut.bat`（防火墙真断 12 秒后自动恢复并删规则，需管理员）、`demo-disconnect.bat`（免管理员备选）、`reconnect-drill.bat`（人工演练回填）。用法与实测数字见 `docs/00-project/demo-runbook.md` §3.5 与 `docs/00-requirements/r013-demo-readiness.md` §10.6。
- 注：准备演示**不要**用 `db_init.py --reset --seed`（会清掉手工建的演示房）；用 `python backend/scripts/clean_demo_junk.py --yes` 只清测试垃圾。

## 4. 设计说明导读（评审按图索骥）

作业「设计说明」九节要求的逐项对号入座表在 `docs/00-project/assignment-a-coverage.md` §6（唯一一处，本页不重抄）。关键入口：

- **架构 / 权限 / 安全**：`docs/01-architecture/r001-app-architecture.md`（§5 配置与密钥、§13 安全）；实时层增量 `docs/01-architecture/r002-realtime-architecture.md`、`docs/01-architecture/r004-realtime-extras-architecture.md`
- **表结构**：`backend/app/db/sql/001_schema.sql`（手写 SQL 即交付物）+ 模块页 `docs/02-modules/r001-rooms.md`
- **LiveKit 与两个自定义能力（举手 / 焦点）**：`docs/02-modules/r002-livekit{,-features}.md`、`r004-room-extras{,-features}.md`；优先级规则见 ADR-0014、授权见 ADR-0021
- **等候室与踢人流程**：`docs/02-modules/r002-livekit-features.md`（F-17）、ADR-0011
- **纪要生成链路**：`docs/02-modules/r008-assignment-gaps.md` §1、ADR-0018
- **语音转写链路**（加分②的一部分）：`docs/02-modules/r010-transcription.md`、ADR-0023
- **失败与边界 / 未完成项**：各轮 `docs/rounds/rNNN-*/design.md` 的「失败与边界」+ 各轮 `docs/rounds/rNNN-*/review.md` 的「未闭合清单」+ 本页 §6

## 5. 验证证据索引

| 命令 | 最近实测 | 出处 |
| --- | --- | --- |
| `pytest backend/tests -q` | **212 passed**（2026-09-20） | `docs/rounds/r013-demo-readiness/review.md` §E11（此后后端代码未再改动） |
| `python backend/scripts/smoke.py --base-url http://127.0.0.1:8000` | **PASS 59/59**（2026-09-20 本页定稿时复跑） | 同上 |
| `npx tsc --noEmit --project frontend` + `npm run build` | exit 0（2026-09-20，cp-15 / cp-16 之后复跑） | 同上 |
| 真机自检 5 份（台本 UI / 台本行为流 / 超管隐身 / 三人档焦点 / 强停共享） | 30-30 · 18-18 · 17-17 · 8-8 · 0.5 秒清格 | `docs/rounds/r013-demo-readiness/review.md` §E1 / §E3 / §E9 / §E10 / §E11 |

必做 15 条与加分 5 项的逐条状态、实现位置与证据：`docs/00-project/assignment-a-coverage.md` §2 / §3。

## 6. 已知边界与未完成项（如实登记）

| 项 | 现状 | 详情 |
| --- | --- | --- |
| 加分① 断线重连后举手 / 焦点恢复 | **已做且有真机取证**：防火墙真断 12 秒 → 断中两端 1.0 / 3.0 秒进「正在重连…」，恢复后 5~6 秒自回「已连接」，举手保持、地址栏不变；界面口径为「非用户主动的中断一律按正在重连处理、不显示已断开」 | `docs/00-requirements/r013-demo-readiness.md` §10.6 / §10.8 / §10.9 |
| 加分② 房间录制 / 旁路转写 | 转写链路**已完成**；**录制经本人决定不做** | `docs/00-project/assignment-a-coverage.md` §3 |
| 加分③ Docker Compose / 公网部署 | **未做**（本机 `dev.bat` 起服务） | 同上 |
| 加分④ 简单管理后台 | **已完成**（r012：房间 / 用户 / 纪要 / 审计四分区 + 结束 / 重生纪要 / 删除三动作；超管隐身进房） | `docs/rounds/r012-superadmin-console/` |
| 加分⑤ 演示录屏 3–5 分钟 | **未做：时间来不及**（分镜 / 逐步脚本 / 道具都已备，缺录制与剪辑；现场可直接演示） | §2.1；`docs/00-project/demo-runbook.md` §5 |
| 转写 worker 的 FFI panic 根因 | 未修（需升级 `livekit-agents`）；现为**自愈 + 可观测**（有限重试、失败以退出码交守护重启、错误透出到界面芯片） | `docs/rounds/r013-demo-readiness/review.md` §6 ① |
| 强停共享的网络级硬断形态 | 已测「共享者直接关标签」路径（0.5 秒清格）；网络层硬断只对断线重连做过，未对共享重跑 | 同上 §6 ② |
| 自检脚本并发抖动 | 多套无头 Chrome 并发时首连偶发超时，建议**逐套串行**跑 | 同上 §6 ④ |

## 7. 提交前 checklist

- [x] 投入小时数（**约 12 小时**）已填 `docs/00-project/ai-tools-and-models.md` §3
- [ ] 补 `docs/00-project/ai-tools-and-models.md` §1 工具行（除 Hermes Agent 外还有没有别的；没有就写「无其它」）
- [ ] 决定 GitHub 仓库公开性并建远端推送（当前仓库**无 remote**）
- [ ] 演示录屏（加分⑤）：**本次因时间来不及不做**（§2.1），若补做按 `docs/00-project/demo-runbook.md` §5「录屏分镜」
- [ ] 打 zip（命名见 §2），核对包内无 `.env` / `node_modules` / 测试残留
- [ ] 合并需求分支并打 `round-rNNN-done`（由本人执行，顺序见 `docs/00-project/global-roadmap.md`）

## 8. 变更记录

| 日期 | 版本 | 改了什么 | 依据 |
| --- | --- | --- | --- |
| 2026-09-20 | v1 | 建页：交付物四项对照、提交口径、起服务与演示、设计说明导读、验证证据索引、已知边界、提交前 checklist | 本人 2026-09-20「写交付文档（用来交付面试作业，题目一）」 |
| 2026-09-20 | v2 | 补 §2.1「时间投入与取舍」：总制作 ≈ 12 小时；**演示录屏因时间来不及未做**（分镜/脚本/道具齐备，仅缺录制剪辑）；交付物④与 checklist 同步（小时数已填、录屏移出待办） | 本人 2026-09-20「加入解释：演示视频时间来不及没做，总制作时间约 12 小时」 |
