---
title: r013 审查与验收对账
description: 演示就绪五项的验收逐条对账（E1~E12）、规则核对、真机证据、未闭合项与合并指引。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-20
rounds: [r013]
---

<!-- overview -->
事实源：`docs/00-requirements/r013-demo-readiness.md`（验收 E1~E12）、`docs/rounds/r013-demo-readiness/design.md`。本页在 cp-7 定稿。

## 1. 验收逐条对账（E1~E12）

| # | 条目 | 实现位置 | 证据 | 结论 |
| --- | --- | --- | --- | --- |
| E1 | 三人档焦点三端一致 | `frontend/scripts/verify-focus-three-way.py`（三隔离 Chrome） | **PASS 8/8 ×3 次**（2026-09-20 实测）：三端 `data-stage-mode=focus`、`.is-focus` 各 1、焦点 identity 三端同为 `usr_012cc…`；另有 1 次定向复跑（举手→房主端举手格 **2.0 秒**出现、服务端 hands 1 条、第三端同步） | **通过（原现象不复现）** |
| E2 | 焦点不受名册/时序影响 | 同上（三人刚进房即给焦点，未等名册刷新） | 三次运行均在进房后 6 秒内给焦点，三端一致 | **通过** |
| 待填 | E3~E12 | | | 见对应 cp |

## 6. 未闭合清单（交你复核）

（cp-7 填）

## 8. 变更记录

| 日期 | 版本 | 改了什么 | 依据 |
| --- | --- | --- | --- |
| 2026-09-20 | cp-2 | E1/E2 对账：三人档焦点**不复现**，脚本三次全绿；登记脚本三条踩坑 | `verify-focus-three-way.py` 实测 |
| 2026-09-20 | 骨架（cp-1） | 建页 | 需求单 §8 |
