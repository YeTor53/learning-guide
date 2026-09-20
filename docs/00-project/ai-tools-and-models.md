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
| 语音转文字（r010，规划） | 云端 Whisper 兼容 REST（方案已定，ADR-0022）；备选：本地 faster-whisper（离线兜底）/ LiveKit Agents 侧（迁移点）/ 浏览器 Web Speech（不用） | `docs/rounds/r010-transcription/redirect-01.md`、`docs/03-decisions/ADR-0022-transcription-path.md`；`STT_*` 三键已进 `.env.example`（待填值） |

## 3. 使用声明（作业要求）

- 开源模板：**未使用**前端模板（自写 React + Vite + 自写样式）；后端 FastAPI 自写；LiveKit 仅用官方 SDK，**未使用 LiveKit Meet 默认页面**。
- 提交时注明：所选题目 = **A**；实际投入小时数 = （请填）。
- 所有外部服务密钥只在本机 `.env`，未入库、未出现在前端产物。
