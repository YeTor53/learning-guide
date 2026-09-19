---
title: r008 需求单：作业必做补全（LLM 纪要 + 限时邀请）+ 语音转文字
description: 三条需求的读back、验收 E1~E12、cp 切分、外部依赖与需要人提供的密钥。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
起因：面试作业「题目 A」覆盖核对（`docs/00-project/assignment-a-coverage.md`）发现两个必做缺口；你 2026-09-19 回 `Q1=1`（先补必做缺口）。设计：`docs/rounds/r008-assignment-gaps/design.md`。

## 1. 三条需求

| # | 需求 | 作业对应 | 现状 |
| --- | --- | --- | --- |
| R1 | **LLM 讨论纪要**：一键生成（房主/协管，结束后也可），调 OpenAI 兼容 LLM，落库 `session_summaries`，房间可查看 | 必做「会后产出」+ 数据层 `session_summaries` + 设计说明「纪要生成链路」+ 冒烟最后一步 | 无表、无服务、无路由、无页面 |
| R2 | **限时邀请**：生成带**过期时间**的邀请链接/房间码；用码可直接加入（容量校验）；过期/用尽/非法明确报错 | 必做「邀请：可生成限时邀请链接或房间码（需设置过期时间）」 | `invites` 表已建（`code/expires_at/max_uses/used_count`），无业务代码 |
| R3 | **语音转文字**：房内把发言转成文字（本端麦克风分段 → 服务端 STT → 落库），文本进纪要输入；界面可看片段 | 加分「旁路录音转写后再生成纪要」 | 无 |

## 2. 口径与边界（读back）

- **纪要**：输入 = 房间主题/标题/简介 + 在册成员（角色/是否在场）+ 近期聊天与系统消息 + **转写文本（有则带）**；输出 markdown 正文；一间房一份、可覆盖重生；**不在结束瞬间自动跑**（结束页给按钮），避免外部调用失败污染结束流程。
- **邀请**：Host/Moderator 可生成；默认 **24 小时**、默认 **1 次**（可改）；用码加入 = **直接成为在册成员**（跳过等候室），仍受 8 人上限（满员 409 `ROOM_FULL`）；复制链接 `/join?code=XXXX`。
- **语音转文字**：**本端麦克风**分段（默认 15 秒/段）→ 后端 STT → 落 `transcripts`；默认**关闭**、本人手动开（提示会上传语音）；未配密钥 503 `STT_NOT_CONFIGURED`；**不做服务端混音录制**（如实写进设计说明）。

## 3. 验收条目

| # | 条目 | 证据 |
| --- | --- | --- |
| E1 | 迁移 `007_r008_session_summaries.sql` 落库（表 + room_id 唯一索引 + 状态 CHECK） | `db_init` 输出 + 表结构 |
| E2 | `POST /rooms/{id}/summary`：管理身份可生成；成功写 `ready` 并返回正文；外部失败写 `failed` + 502 `SUMMARY_FAILED`；未配密钥 503 `LLM_NOT_CONFIGURED` | `pytest`（打桩）+ 真实 HTTP |
| E3 | 重复生成 = 覆盖同一行，`updated_at` 前进（`clock_timestamp()`） | 用例断言 |
| E4 | `GET /rooms/{id}/summary`：房内在册成员或管理身份可看；未生成 `summary: null` | 用例 |
| E5 | 前端：已结束房间卡片有「讨论纪要」入口 → 纪要页可看正文、可生成/重生；未配密钥给出明确提示 | 真机截图 + DOM |
| E6 | 冒烟补「生成纪要」一步：配了密钥断言 `ready`，未配断言 `503 LLM_NOT_CONFIGURED`（两分支如实） | `smoke` 输出 |
| E7 | `POST /rooms/{id}/invites` 返回 `code/expiresAt/maxUses`；非法 TTL/次数 400 | 用例 |
| E8 | `POST /invites/{code}/accept`：有效 → 在册 + 系统消息；过期/用尽/非法 → 400 `INVITE_INVALID`；满员 → 409 `ROOM_FULL`；已在册 → 幂等 200 | 用例 |
| E9 | 前端：抽屉「邀请」区（生成 + 复制 + 到期）；`/join?code=` 凭码加入页 | 真机截图 + DOM |
| E10 | `POST /rooms/{id}/transcripts`（音频上传）→ 配好 STT 写 `ready` 并返回文本；未配 503 `STT_NOT_CONFIGURED` | 用例（打桩）+ 真机（有 key 时） |
| E11 | 房内「转写」开关 + 片段列表（本人可见自己的，管理身份可见全部） | 真机截图 + DOM |
| E12 | 门禁全绿；README / 设计说明 / `.env.example` 三处同步（含 `STT_*`） | 命令输出 |

## 4. 需要你提供（否则只能跑「未配置」分支）

| 用途 | 键 | 备注 |
| --- | --- | --- |
| 纪要生成 | `LLM_API_KEY` | 现在是空的；`LLM_BASE_URL`/`LLM_MODEL` 已填（DeepSeek）；任意 OpenAI 兼容均可 |
| 语音转文字 | `STT_BASE_URL` / `STT_API_KEY` / `STT_MODEL` | 新增三键；Whisper 兼容 `/audio/transcriptions` |

> 不给也能推进：代码 + 用例走打桩，真机跑「未配置提示」分支；key 到位我再补真机成功取证。

## 5. cp 切分

| cp | 内容 |
| --- | --- |
| cp-0 | 阶段 1 文档（需求单 + design + 台账 + ADR-0018~0020 + 索引与 roadmap） |
| cp-1 | 纪要后端（迁移 007 + 服务 + 路由 + 用例） |
| cp-2 | 纪要前端（纪要页 + 卡片入口） |
| cp-3 | 限时邀请（后端 + 前端 + 用例） |
| cp-4 | 语音转文字（迁移 008 + STT 服务 + 上传路由 + 前端） |
| cp-5 | 收官（冒烟补步、README/设计说明回填、门禁、review 定稿） |

## 6. 变更记录

| 日期 | 版本 | 改了什么 | 依据 |
| --- | --- | --- | --- |
| 2026-09-19 | v1 | 建页：三件需求 + 口径 + E1~E12 + cp 切分 + 密钥需求 | 你 `Q1=1` + 「再加一个语言转文字需求」 |
