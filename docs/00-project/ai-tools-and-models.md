---
title: 使用的 AI 工具与模型列表（作业交付物）
description: 提交前请补齐——开发过程中用到的编程助手、对话模型与推理服务清单。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-20
---

<!-- overview -->
作业原文要求「提交时列出工具与模型；你需能讲清架构、关键决策与验证方式」。**本页需你本人确认后再交**（我只能填我这边确实用过的）。
**本页 `status: draft`**：§1 表中「请补」行等 owner 确认后随交付提交（r009.5 只纠轮次号与路径，不代填）。

## 1. 编程 / 研究工具

| 工具 | 用在哪 | 备注 |
| --- | --- | --- |
| Hermes Agent（本仓开发代理） | 需求梳理、设计文档、前后端实现、用例与真机验证（Playwright） | 全程留痕在 git 提交与 `docs/` |
| （请补：如 Claude Code / Codex / Cursor 等） |  |  |

## 2. 模型

| 用途 | 模型 / 服务 | 备注 |
| --- | --- | --- |
| 开发期对话与代码（代理模型） | `deepseek-v4-flash`（经 Hermes Agent 调用） | 本仓提交与文档由它产出与核对 |
| 纪要生成（产品功能，运行时调用） | `LLM_MODEL`（当前 `.env` 指向 DeepSeek `deepseek-chat`），OpenAI 兼容接口 | 见 `.env.example` 的 `LLM_*`；真机实测 6.0 秒 / 632 字 |
| 语音转文字（r010，**已实现 2026-09-20**） | **换轨后口径**：识别在**房间侧**（LiveKit Agents worker + **LiveKit Inference**，实测免自备 key、中文可用）；B 路径「云端 Whisper 兼容 REST」保留但不激活（`STT_MODE=backend` 可切）；备选：本地 faster-whisper（离线兜底）/ 浏览器 Web Speech（不用） | `docs/03-decisions/ADR-0023-agent-side-transcription.md`（取代 ADR-0022 的 D1）、`docs/rounds/r010-transcription/spike-01-path-a.md`（含配额单价实测）、`docs/02-modules/r010-transcription.md`；`.env.example` 新增 `STT_MODE/STT_AGENT_NAME/STT_MAX_SESSIONS`（`STT_*` 三键仅 B 路径需要） |

## 3. 使用声明（作业要求）

- 开源模板：**未使用**前端模板（自写 React + Vite + 自写样式）；后端 FastAPI 自写；LiveKit 仅用官方 SDK，**未使用 LiveKit Meet 默认页面**。
- 提交时注明：所选题目 = **A**；**实际投入小时数 ≈ 12 小时**（2026-09-20 本人确认口径；含需求与设计文档、后端与数据库、前端、测试与文档回填的合计，不含未做的演示录屏）。
- 加分项时间取舍（演示录屏为何没做等）：见 `docs/00-project/global-delivery.md` §2.1。
- **部署声明：未使用 Docker（本机未安装），未做 Docker Compose / 公网部署**；起服务 = 本机 `dev.bat` 两个进程，交付与演示形态 = uvicorn 托管前端 `dist` 的单进程同源（`.env` 的 `APP_ENV=demo`）。
- 所有外部服务密钥只在本机 `.env`，未入库、未出现在前端产物。
