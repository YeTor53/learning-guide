---
title: 需求单索引（按轮次）
description: 项目各轮需求单的状态、里程碑归属与轮次档案入口。
type: reference
status: approved
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
一轮一行；需求单正文在 `docs/00-requirements/rNNN-*.md`，轮次档案在 `docs/rounds/rNNN-*/`。

| 轮次 | 里程碑 | 需求单 | 状态 | 轮次档案 | 完成 tag |
| --- | --- | --- | --- | --- | --- |
| r001 | M1 骨架 · 账户 · 房间 | `r001-skeleton-accounts-rooms.md` | closed（2026-09-18） | `docs/rounds/r001-skeleton/` | `round-r001-done`（2026-09-18 由人执行；合并提交 `c189a87`） |
| r002 | M2 实时房间 · 权限 · 等候室 | `r002-livekit-room.md` | **closed**（2026-09-18 收官；2026-09-19 由 r003 回填定稿） | `docs/rounds/r002-livekit/`（含 `redirect-01..07`） | `round-r002-done`（2026-09-18 由人执行；合并提交 `7f2e994`，`main` = `b8783d2`；cp tag 只有 2/3/4） |
| r003 | （补轮）交付前修补：房主结束房间入口 + r002 收官回填 | `r003-end-room-entry.md` | **closed**（2026-09-19 收官；收官回填由 r004 `cp-2` 完成） | `docs/rounds/r003-end-room-entry/`（含 `redirect-01..02`） | `round-r003-done`（2026-09-19 由人执行；合并提交 `694caeb`；cp tag 1/2/3 齐） |
| r004 | M3 自定义能力 · 群聊（+ 举手 / 焦点发言 / 屏幕共享 / 优先级 / 界面缺陷 / 还债） | `r004-room-extras.md` | **实现完成（cp-2~cp-7 全绿，2026-09-19）；待合并** | `docs/rounds/r004-room-extras/`（review.md 已定稿） | 合并后由人打 `round-r004-done`（cp tag `cp-r004-1..7` 已齐） |
| r005 | （补轮）容量口径修正：人数上限按本库在册成员（不再以 LiveKit 为准）+ 房间事件进消息列表 + 取票提速 | `r005-fix-capacity.md` | draft（实现中，2026-09-19） | `docs/rounds/r005-fix-capacity/` | 合并后由人打 `round-r005-done`（cp tag `cp-r005-0..4`） |