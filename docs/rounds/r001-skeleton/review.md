---
title: r001 轮次档案 · 审查结论
description: r001 的验收对账结论、规则核对、遗留清单与合并指引。
type: reference
status: closed
owner: 陀梓皓
updated: 2026-09-18
---

<!-- overview -->

## 1. 验收对账（对照需求单 §3）

§3 共 20 项，**全部闭合**：18 项由自动检查覆盖（E1~E8：`db_init` 行数、`pytest 72 passed`、`smoke PASS 22/22`、前端 `tsc`+`build`、密钥检索、`git` 状态、两条 SQL 取证）；2 项由 2026-09-18 浏览器实操覆盖（E9 九步演示、E10 未登录引导与 `returnTo` 回跳）。逐条证据见需求单 §3.1。

## 2. 规则核对（AGENTS.md）

| 规则 | 结论 |
| --- | --- |
| 未获批准不做实现 | 四页（总设计 / 需求单 / 房间两页）转 approved 后才建分支开工 |
| 一次提交 = 一个逻辑增量 + `[Req: r001]` | 13 个 checkpoint，逐提交核对通过 |
| `git add` 只写具体路径 | 全程按路径 add，未用 `-A` |
| 分支 / tag 命名 | `req/r001-skeleton` + `cp-r001-1..13`；`round-r001-done` 待人合并后打 |
| 历史 append-only | 无 amend / rebase / squash |
| 文档与代码同一次提交 | 每个增量提交均含对应文档改动（含两处 ADR 与风格指南同步） |
| 不擅自增删依赖 | `lucide-react` 与全部前端依赖已登记在需求单 §2 |
| 密钥不入库 | `.env` 未入库；`git grep` 仅命中 `config.py` 的变量名 |

## 3. 遗留与未做（完整清单见 `docs/00-project/global-roadmap.md` §9 / §9.1）

- 测试欠账两条：分页 `limit/offset` 用例、房间码冲突重试分支用例（低风险）。
- 行为待定一条：房间结束后 `myRole` 为 `null`（历史角色不显示徽标）→ r002 决定。
- 上游噪音：`pytest` 输出 Starlette/httpx 弃用告警，待上游。
- §9.1 暂留（2026-09-18 讨论结论已留档）：跨房间「在场唯一」不做硬约束；外部同类项目可抄五项；两处实现缺口（非管理者申请人撤不回申请、同房间成员历史重复行）暂未排期。

## 4. 合并指引（AGENTS 硬规矩 4：由人执行）

```bash
git checkout main
git merge --no-ff req/r001-skeleton
git tag -a round-r001-done -m "r001 完成（M1 骨架 · 账户 · 房间）"
# 主干复验（<check>）
python backend/scripts/db_init.py --reset --seed
pytest backend/tests -q
python backend/scripts/smoke.py          # 需后端以 APP_ENV=dev 运行
cd frontend && npx tsc --noEmit && npm run build
```

## What's next

r002 = M2：LiveKit 接线（服务端签 Token、`max_participants` 兜底、踢人的 Token 失效分支）、批准后真正进房、三角色权限矩阵落地、踢人；轮次设计见 `docs/rounds/r002-livekit/design.md`（模块页 `docs/02-modules/r002-livekit.md`）。
