---
title: ADR-0020：转写按本端麦克风分段（非服务端混音录制）
description: 决定、理由、取舍与影响面（r008）。
type: reference
status: proposed
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
出处：`docs/rounds/r008-assignment-gaps/design.md`。

## 决定

**决定**：v1 只做**本端麦克风** 15 秒分段 → 后端 STT（Whisper 兼容）→ 落 `transcripts`；默认关闭、本人主动开启并提示会上传语音；文本可见性 = 本人 + Host/Moderator。不做服务端 egress 混音录制（作为未完成项写入设计说明）。

**理由**：加分项只要求「录制或旁路录音转写后生成纪要」；本端分段零额外基础设施、隐私可控、可复核。

## 影响面

- 数据：`docs/rounds/r008-assignment-gaps/design.md` §1
- 接口：同页 §2.8
- 前端：同页 §3
- 作业覆盖：`docs/00-project/assignment-a-coverage.md`

## 变更记录

| 日期 | 版本 | 改了什么 | 依据 |
| --- | --- | --- | --- |
| 2026-09-19 | v1 | 建页（r008 cp-0） | 你的批复 `Q1=1` + 「语音转文字」追加 |
