---
title: r008 变更台账
description: cp 台账、文件台账、门禁记录与实测证据。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
验收对照见 `review.md`。

## 1. cp 台账

| cp | 内容 | 状态 | 提交 | 证据 |
| --- | --- | --- | --- | --- |
| cp-r008-0 | 阶段 1 文档（需求单 / design / 台账 / ADR-0018~0020 / 索引与 roadmap） | in_progress | — | —— |
| cp-r008-1 | 纪要后端（迁移 007 + 服务 + 路由 + 用例） | **完成 2026-09-19** | 见 cp-1 提交 | E1~E4（§3.1） |
| cp-r008-2 | 纪要前端（纪要页 + 卡片入口） | planned | — | E5 |
| cp-r008-3 | 限时邀请（后端 + 前端 + 用例） | planned | — | E7~E9 |
| cp-r008-4 | 语音转文字（迁移 008 + 服务 + 路由 + 前端） | planned | — | E10/E11 |
| cp-r008-5 | 收官（冒烟补步 / README / 设计说明 / 门禁 / review） | planned | — | E6/E12 |

## 3. 实测证据

### 3.1 cp-1（纪要后端 E1~E4）

- 迁移 `007_r008_session_summaries.sql` 应用 ✓（`db_init` 输出 `session_summaries` 计数行，`schema_migrations=7`）。
- 真实 HTTP（未配置 LLM 密钥，即当前 `.env` 状态）：
  - `POST /api/rooms/{id}/summary`（房主）→ **503 `LLM_NOT_CONFIGURED`**（不落库）；
  - `GET  /api/rooms/{id}/summary`（未生成）→ **200，`data.summary = null`**；
  - `GET`（非成员）→ **403**；`POST`（非成员）→ **403**。
- 用例（打桩 LLM，5 条）：管理身份校验 403；成功写 `ready` 且重复生成覆盖同一行（库里 1 行、内容更新）；未配置 → 503 且不落库；调用失败 → 502 `SUMMARY_FAILED` 且落 `failed` 行并记原因；可见性（成员 200 / 非成员 403 / 未生成 null）。
- 门禁：`pytest` **118 passed**（原 113）。
- **待你提供 `LLM_API_KEY`**：给了之后我再跑真机成功分支（生成真纪要）取证。
