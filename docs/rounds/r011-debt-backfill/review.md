---
title: r011 审查报告（骨架）：验收对账、两栏清单与合并指引
description: cp-1 建骨架；cp-6 定稿时逐条给证据（命令输出 / 文件行 / 用例名）。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-20
---

<!-- overview -->
**定稿**：cp-r011-6。需求单 `docs/00-requirements/r011-debt-backfill.md`；设计 `docs/rounds/r011-debt-backfill/design.md`；剧本 `docs/rounds/r011-debt-backfill/manual-verification.md`。

## 1. 验收对账（cp-6 填）

| # | 条目 | 证据 | 结论 |
| --- | --- | --- | --- |
| E1 | A 组 4 类回填落地 | 待填 |  |
| E2 | r002 §4 36 条逐条有状态 | 待填 |  |
| E3 | r005 §4 8 条逐条有状态 | 待填 |  |
| E4 | 满员自动拒（用例 + 真机） | 待填（MV-9 步 4） |  |
| E5 | 邀请码入口 + `returnTo` 闭环 | 待填（MV-9 步 1/2） |  |
| E6 | worker 健康上报显示 | 待填（MV-9 步 5） |  |
| E7 | `STT_MODE=off` 用例 | 待填 |  |
| E8 | 门禁四项复跑 | 待填（changes §2） |  |
| E9 | 文档 = 代码（无 `planned` 残留） | 待填 |  |
| E10 | 剧本覆盖 MV-1~MV-9 | cp-1 已交付（`manual-verification.md`） | 通过（交付物本身） |

## 2. 规则核对（AGENTS.md / 本轮纪律）

待填：每处改动挂在 r011 上；一次提交一个逻辑增量；`git add` 只写具体路径；历史 append-only（不 amend / 不 rebase）；密钥不入库；补正轮例外项在 design §6 有授权依据。

## 3. 文档对账

两轴（项目级 / 轮次）：待填。至少覆盖 README / AGENTS / coverage / 需求索引 / roadmap §7 §9 / 需求单勾选 / 模块轴变更记录。

## 4. 人工取证

MV-1~MV-9 的执行结果与回填位置见 `manual-verification.md`；未跑的一律标「未取证」。

## 5. 两栏处置清单（cp-6 定稿）

**本轮已落地可保留**：待填。
**未闭合 / 如实说明**：待填。

## 6. 合并指引（由人执行）

```
git checkout main
git merge --no-ff req/r011-debt-backfill
git tag -a round-r011-done -m "r011 完成（欠账补正 + 三处授权例外）"
```
合并后复验：`pytest backend/tests -q` → `python backend/scripts/smoke.py --base-url http://127.0.0.1:8000` → `cd frontend && npx tsc --noEmit && npm run build`。
