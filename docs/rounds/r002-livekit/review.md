---
title: r002 审查报告（阶段 3 用）
description: r002 的验收对账、规则核对、可保留增量清单、未闭合项与合并指引（收官时定稿）。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-18
---

<!-- overview -->
阶段 3 的产物：对照需求单逐条给证据、对照 `AGENTS.md` 与 `docs/04-style/` 核对规则、两轴文档对账、CR 对账；
并给用户两栏处置清单（可保留增量 / 未闭合项）。**收官前本页为骨架。**

## 1. 验收对账（需求单 §4 逐条）

| 验收条目 | 实现位置 | 证据 | 结论 |
| --- | --- | --- | --- |
| （实现后逐条填） | | | |

## 2. 规则核对（AGENTS.md / 风格指南）

| 规则 | 核对方式 | 结论 |
| --- | --- | --- |
| `API_SECRET` 不进前端/产物/日志 | `git grep` + 检索 `frontend/dist` | 待核 |
| 不擅自增删依赖（两项依赖经批准） | 需求单 §9 的批准记录 | 待核 |
| 提交规范（一 cp 一提交一 tag、`git add <路径>`、append-only） | `git log --oneline` + `git tag` | 待核 |
| 界面：Lucide 图标、零 emoji、文案禁内部词 | 扫 `frontend/src` 文案词表 + 浏览器 `innerText` | 待核 |
| 错误提示三分流（401 / 业务码 / 网络） | 房内页四态实测 | 待核 |

## 3. 文档对账（两轴 + 四件套 + 覆盖矩阵）

| 项 | 结论 |
| --- | --- |
| 模块轴：设计页 / 实现页 / 使用者教学页 / 开发者教学页 | 待核（教学两页随 cp-4） |
| 轮次轴：`docs/rounds/r002-livekit/` 档案齐（design/changes/review/CR） | 骨架已建 |
| 索引：`docs/00-requirements/README.md` 有 r002 行；模块页「变更记录」回填本轮 | 待核 |
| 覆盖矩阵：无空格、无 `planned` 残留 | 待核 |

## 4. 口径对账

- 外部服务契约：Token 字段来自 LiveKit 官方（`video.room` / `roomJoin` / `roomAdmin` / `roomConfig.max_participants`），实现未自拟字段名 —— 待核（对照 `docs/02-modules/r002-livekit.md` §6.4 与实测 JWT 解码输出）。
- 密钥口径：Secret 只在 `.env` 与后端进程 —— 待核（检索命令取证）。

## 5. 设计变更对账

| CR | 级别 | 结论 | 落地 SHA |
| --- | --- | --- | --- |
| （实现期追加） | | | |

## 6. 留给用户的两栏处置清单

**本轮已落地可保留的增量**（各带 SHA 与文档页）：待实现后填。

**未闭合项 / 半成品**（各带「若判为 C 或 D 时的处置」）：待实现后填（预期候选：R-8 自建模式的 Token 失效说明、离线成员的清位口径、M3 的房内能力入口预留）。

## 7. 合并指引（由人执行，AGENTS 硬规矩 4）

```
git checkout main
git merge --no-ff req/r002-livekit
git tag -a round-r002-done -m "r002 完成（M2 实时房间 · 权限 · 等候室）"
```

合并后主干复验：`python backend/scripts/db_init.py --reset --seed` → `pytest backend/tests -q` → `python backend/scripts/smoke.py`（后端需 dev 形态）→ `cd frontend && npx tsc --noEmit && npm run build`。
