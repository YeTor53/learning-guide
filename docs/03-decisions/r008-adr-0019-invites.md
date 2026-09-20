---
title: ADR-0019：邀请码直接成为在册成员（跳过等候室，仍受上限）
description: 决定、理由、取舍与影响面（r008）。
type: reference
status: proposed
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
出处：`docs/rounds/r008-assignment-gaps/design.md`。

## 决定

**决定**：`POST /rooms/{id}/invites` 生成 `code`（8 位、小写存储、唯一索引）、`expires_at`（默认 24h，可 1 分钟~7 天）、`max_uses`（默认 1，可 1~50）；`POST /invites/{code}/accept` 校验通过后直接建在册成员并 `used_count+1`，写系统消息「X 通过邀请链接加入」；过期/用尽/非法 → 400 `INVITE_INVALID`；满员 → 409 `ROOM_FULL`；已在册 → 幂等 200。

**理由**：作业把「邀请」与「等候室」并列；邀请的语义是「房主已同意你来了」；仍走容量校验保证 8 人上限不被绕过。

## 影响面

- 数据：`docs/rounds/r008-assignment-gaps/design.md` §1
- 接口：同页 §2.8
- 前端：同页 §3
- 作业覆盖：`docs/00-project/assignment-a-coverage.md`

## 变更记录

| 日期 | 版本 | 改了什么 | 依据 |
| --- | --- | --- | --- |
| 2026-09-19 | v1 | 建页（r008 cp-0） | 你的批复 `Q1=1` + 「语音转文字」追加 |
