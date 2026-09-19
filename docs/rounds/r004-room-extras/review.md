---
title: r004 审查报告（阶段 3 用）
description: r004 的验收对账、规则核对、两轴文档对账、CR 与重定向对账、视觉对账、两栏处置清单与合并指引（收官时定稿）。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
阶段 3 的产物：对照需求单 §5 的 E1~E20 逐条给证据、规则核对、两轴文档对账、CR 与重定向对账、视觉对账，并给用户两栏处置清单。**收官前本页为骨架。**

## 1. 验收对账（需求单 §5 的 E1~E20）

| 条目 | 实现位置 | 证据 | 结论 |
| --- | --- | --- | --- |
| E1~E6（后端） | 待实现后填 | | |
| E7（tsc/build） | | | |
| E8~E14（双浏览器与优先级） | | | |
| E15（两项界面缺陷） | | | |
| E16~E17（pytest / smoke） | | | |
| E18~E20（取证报告 / 文档对账 / r003 回填） | | | |

## 2. 规则核对（AGENTS.md / 风格指南）

| 规则 | 核对方式 | 结论 |
| --- | --- | --- |
| 未批不实现；每处改动挂 `rNNN` | 提交信息 `[Req: r004]` | 待核 |
| 一次提交一个逻辑增量；`git add` 具体路径；append-only | `git log` | 待核 |
| 零新依赖、不改端口与运行形态 | 依赖文件 diff + `dev.bat` diff | 待核 |
| 密钥不入库 | `git grep` | 待核 |
| 文档与代码同一次提交 | 逐提交 diff | 待核 |
| 零 emoji / 单一图标库 Lucide | `frontend/src` 扫描 | 待核 |

## 3. 文档对账（两轴 + 四件套 + 覆盖矩阵）

| 项 | 结论 |
| --- | --- |
| 模块轴：设计页 / 模块页（实现 + 功能）/ 使用者教学页 / 开发者教学页 | 待核 |
| 轮次轴：`docs/rounds/r004-room-extras/` 三件套齐（design / changes / review） | 待核 |
| 索引 + 模块页变更记录 + 术语表 | 待核 |
| 覆盖矩阵无 `planned` 残留 | 待核 |

## 4. 重定向与 CR 对账

| 单号 | 类型 | 级别 | 结论 | 落地 |
| --- | --- | --- | --- | --- |
| （实现期追加） | | | | |

- CR 预期候选：design §6.1 的「服务端强停共享」实测结果（若降级影响对外可见面 → 补 CR）；焦点优先级若被推翻 → ADR-0014 变更。
- 滑行检查：`design.md` §14 与本表、与 `git log` 三方互核。

## 5. 视觉对账（界面类项目）

| 组 | 方式 | 结果 |
| --- | --- | --- |
| 令牌扫描 | `git grep -- "--chat-bubble-own\|--live-hand-active\|--live-share-badge"` | 待测 |
| 零 emoji / 单一图标库 | 扫描 | 待测 |
| 桌面 + 窄屏截图 | 真机（5173/8000） | 待测 |
| 动效降级 | `prefers-reduced-motion` 模拟 + 截图 | 待测 |
| 几何量测 | 控制坞按钮尺寸一致；焦点格 letterbox | 待测 |

## 6. 留给用户的两栏处置清单

**本轮已落地可保留的增量**：待实现后填。
**未闭合项 / 半成品**：待实现后填（预期候选：M5 的断线后举手/焦点恢复、未读跨页持久化、共享录制的可行性）。

## 7. 合并指引（由人执行，AGENTS 硬规矩 4）

```bash
git checkout main
git merge --no-ff req/r004-room-extras
git tag -a round-r004-done -m "r004 完成（M3 房内扩展能力 · 群聊/举手/焦点/共享 + 界面缺陷与还债）"
```

合并后复验：`dev.bat check` → `pytest backend/tests -q` → `python backend/scripts/smoke.py` → `cd frontend && npx tsc --noEmit && npm run build` → 真机 E8~E14。
