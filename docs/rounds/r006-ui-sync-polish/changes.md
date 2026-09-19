---
title: r006 变更台账
description: 逐文件改动、每 cp 的实测证据与文档产出对账。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
验收对照见 `review.md`；函数级设计见 `design.md`。

## 1. cp 台账

| cp | 内容 | 状态 | 提交 | 证据 |
| --- | --- | --- | --- | --- |
| cp-r006-0 | 阶段 1 文档先行（需求单 / design / ADR-0017 / 台账骨架 / 索引与 roadmap 回填） | in_progress | — | —— |
| cp-r006-1 | 麦徽标改真实麦克风状态（静音事件驱动重渲染） | planned | — | E1/E2 |
| cp-r006-2 | `lg.roster` 同步 + 三个刷新触发点 | planned | — | E3/E4/E5 |
| cp-r006-3 | 个人信息浮窗 + 哲学语句池 | planned | — | E6/E7 |
| cp-r006-4 | 图版初始位置下移 + 前端优化清点处置 | planned | — | E8/E9 |
| cp-r006-5 | 收官（门禁 / r004 欠账 / 文档回填 / review 定稿） | planned | — | E10 |

## 2. 文件台账

| 文件 | 模块 | 改什么 | 落地文档 | 状态 |
| --- | --- | --- | --- | --- |
| `docs/00-requirements/r006-ui-sync-polish.md`（新） | 契约 | 需求/口径回读/验收/cp | 自身 | landed（cp-0） |
| `docs/rounds/r006-ui-sync-polish/{design,changes,review}.md` | 契约 | 函数级设计 / 台账 / 审查 | 自身 | landed（cp-0，review 待定稿） |
| `docs/03-decisions/r006-adr-0017-ui-polish-decisions.md`（新） | 决策 | D1~D4 界面口径 | 自身 | landed（cp-0） |
| `docs/rounds/r006-ui-sync-polish/redirect-01.md` | 契约 | 两例实测 + 定性（原 r006-fix-mic-badge 目录改名而来） | 自身 | landed（改名） |

## 3. 门禁记录

| 时点 | pytest | smoke | tsc | build |
| --- | --- | --- | --- | --- |
| cp-0 | 111 passed（r005 基线） | 40/40 | exit 0 | exit 0 |
