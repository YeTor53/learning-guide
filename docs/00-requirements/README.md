---
title: 需求单索引（按轮次）
description: 项目各轮需求单的状态、里程碑归属与轮次档案入口。
type: reference
status: approved
owner: 陀梓皓
updated: 2026-09-20
---

<!-- overview -->
一轮一行；需求单正文在 `docs/00-requirements/rNNN-*.md`，轮次档案在 `docs/rounds/rNNN-*/`。

| 轮次 | 里程碑 | 需求单 | 状态 | 轮次档案 | 完成 tag |
| --- | --- | --- | --- | --- | --- |
| r001 | M1 骨架 · 账户 · 房间 | `r001-skeleton-accounts-rooms.md` | closed（2026-09-18） | `docs/rounds/r001-skeleton/` | `round-r001-done`（2026-09-18 由人执行；合并提交 `c189a87`） |
| r002 | M2 实时房间 · 权限 · 等候室 | `r002-livekit-room.md` | **closed**（2026-09-18 收官；2026-09-19 由 r003 回填定稿） | `docs/rounds/r002-livekit/`（含 `redirect-01..07`） | `round-r002-done`（2026-09-18 由人执行；合并提交 `7f2e994`，`main` = `b8783d2`；cp tag 只有 2/3/4） |
| r003 | （补轮）交付前修补：房主结束房间入口 + r002 收官回填 | `r003-end-room-entry.md` | **closed**（2026-09-19 收官；收官回填由 r004 `cp-2` 完成） | `docs/rounds/r003-end-room-entry/`（含 `redirect-01..02`） | `round-r003-done`（2026-09-19 由人执行；合并提交 `694caeb`；cp tag 1/2/3 齐） |
| r004 | M3 自定义能力 · 群聊（+ 举手 / 焦点发言 / 屏幕共享 / 优先级 / 界面缺陷 / 还债） | `r004-room-extras.md` | **closed**（2026-09-19 由人合并；收官回填由 r009.5 完成） | `docs/rounds/r004-room-extras/`（review.md 已定稿） | `round-r004-done`（2026-09-19 由人执行；合并提交 `daf7696`；cp tag `cp-r004-1..7` 齐） |
| r005 | （补轮）容量口径修正：人数上限按本库在册成员（不再以 LiveKit 为准）+ 房间事件进消息列表 + 取票提速 | `r005-fix-capacity.md` | **已合并**（2026-09-20，`main` = `96b1153`） | `docs/rounds/r005-fix-capacity/`（review 已定稿） | `round-r005-done`（2026-09-20 由人执行；cp tag `cp-r005-0..4` + `4b`） |
| r006 | （补轮）界面同步与优化：麦克风徽标 / 两端人数与待批同步 / 个人信息浮窗 + 哲学语句 / 图版初始位置 | `r006-ui-sync-polish.md` | **已合并**（2026-09-20，`main` = `96b1153`） | `docs/rounds/r006-ui-sync-polish/`（review 已定稿；教学页缺，见 `docs/README.md` §5） | `round-r006-done`（2026-09-20 由人执行；cp tag `cp-r006-0..5`） |
| r007 | （补轮）首屏向下引导 + 主题控件风格化 + 主题扩容（14 项）+ 侧边栏默认收起 | `r007-topic-and-scrollhint.md` | **已合并**（2026-09-20，`main` = `96b1153`） | `docs/rounds/r007-topic-and-scrollhint/`（review 已定稿；教学页缺，见 `docs/README.md` §5） | `round-r007-done`（2026-09-20 由人执行；cp tag `cp-r007-0..8`） |
| r008 | （补轮·作业必做补全）讨论纪要（LLM）+ 限时邀请（最长 1 分钟） | `r008-assignment-gaps.md` | **已合并**（2026-09-20，`main` = `96b1153`）；r009.5 已补正台账与审查 | `docs/rounds/r008-assignment-gaps/`（review 已定稿） | `round-r008-done`（2026-09-20 由人执行；cp tag `cp-r008-0..4`） |
| r009 | （补轮）焦点系统重做：均分铺满 + 举手经管理确认得焦点 + 协管需他人批准 + 退出焦点 + 声波 | `r009-focus-system.md` | **已合并**（2026-09-20，`main` = `96b1153`；cp-0~cp-5）；r009.5 已补正台账与审查（E0/E1/E2/E7/E12 回填、cp tag 补齐） | `docs/rounds/r009-focus-system/`（review 已定稿） | `round-r009-done`（2026-09-20 由人执行；cp tag `0/1a/1b/2a/2b/3a/3b/5`；4 无独立提交） |
| r010 | （实现轮）语音转文字并入讨论流（**换轨 Agents 侧识别**，ADR-0023） | `r010-transcription.md` | **已合并**（2026-09-20，`main` = `96b1153`；cp-1~cp-6 + spike-01 + CR-01/02） | `docs/rounds/r010-transcription/`（含 `cr-01/02.md`、`spike-01-path-a.md`、review 定稿） | `round-r010-done`（2026-09-20 由人执行；cp tag `cp-r010-*`） |
| r009.5 | （补正轮）r008/r009 欠账补正：台账 · tag · 审查回填 · 纠错 · 取证 · 教学页 | `r009.5-debt-backfill.md` | **已合并**（2026-09-20，其 7 个提交随 r010 一并合入 `96b1153`） | `docs/rounds/r009.5-debt-backfill/`（review 已定稿） | `round-r009.5-done`（2026-09-20 由人执行；cp tag `cp-r009.5-1..5`） |
| r011 | （补正轮）欠账补正 + 四处授权例外（满员自动拒待批申请 / 邀请码入口与未登录闭环 / worker 健康上报 / **焦点规则收窄：说话不获焦点**） | `r011-debt-backfill.md` | **实现完成，待合并**（2026-09-20：cp-1~cp-7 全落，pytest 164 / smoke 47-47 / tsc · build 绿；人工剧本 MV-1~MV-11 待你跑） | `docs/rounds/r011-debt-backfill/`（含 design / redirect-02 / manual-verification / changes / review 定稿） | 合并后由人打 `round-r011-done`（cp tag `cp-r011-1/1b/2/3/4/5/6/6b/7`） |

> **合并顺序（2026-09-20 r009.5 登记）**：`r005 → r006 → r007 → r008 → r009 → r010 → r009.5`。r005~r010 与 r009.5 于 **2026-09-20 全部合入 `main` = `96b1153`**（`round-r005-done` … `round-r010-done`、`round-r009.5-done` 齐）；r011 从该 HEAD 开出，本轮无前置未合并轮次。|