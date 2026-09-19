---
title: ADR-0018：讨论纪要落在 session_summaries（覆盖式重生，失败也留痕）
description: 决定、理由、取舍与影响面（r008）。
type: reference
status: proposed
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
出处：`docs/rounds/r008-assignment-gaps/design.md`。

## 决定

**决定**：纪要一间房一份（`room_id` 唯一索引），重复生成为覆盖写（`created_at` 首次、`updated_at` 前进）；成功写 `ready`、失败写 `failed` 并记 `error`；未配置密钥不落库、直接 503。

**理由**：作业要求「结束后自动或一键生成、落库、详情页可查看」；一间房一份便于评审复现；失败留痕能回答「失败与边界」的提问。

**取舍**：不做版本历史（要的话下一轮加 `revision` 列）。

## 影响面

- 数据：`docs/rounds/r008-assignment-gaps/design.md` §1
- 接口：同页 §2.8
- 前端：同页 §3
- 作业覆盖：`docs/00-project/assignment-a-coverage.md`

## 变更记录

| 日期 | 版本 | 改了什么 | 依据 |
| --- | --- | --- | --- |
| 2026-09-19 | v1 | 建页（r008 cp-0） | 你的批复 `Q1=1` + 「语音转文字」追加 |
