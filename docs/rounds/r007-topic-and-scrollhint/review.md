---
title: r007 审查报告（阶段 3）
description: E1~E7 逐条证据、规则/视觉对账、两栏清单与合并指引（cp-5 定稿）。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
状态：**骨架**（cp-5 定稿）。

## 1. 验收对账

| 条目 | 证据 | 结论 |
| --- | --- | --- |
| E1 工具栏回到 hero 下方 | 1440×900：`toolbar 841→886`、`hero 101→801` → 间距 **40px**；1258×566：`toolbar 639`（回到原位） | **通过** |
| E2 浮动下箭头 | `role=presentation`、`aria-hidden=true`、`pointer-events: none`、无 `onclick`；`animation: scroll-hint-bob`，reduced-motion 下 `none` | **通过** |
| E3 首页主题自绘下拉 | 原生 `select` **0**；面板 `role=listbox`/`aria-expanded=true`/15 项（14 带图标）；`↓↓`+`Enter` 选中「数理生物学」；`Esc` 关闭并回焦；点外关闭 | **通过** |
| E4 创建房间主题卡片 | 14 张 `.topic-card`，全部带图标 + 用途；`role=radio`/`aria-checked` 唯一切换 | **通过** |
| E5 主题扩容 | 迁移 006 应用（`schema_migrations=6`）；三处白名单顺序一致；新主题建房 201 / 非法 400 / 未知主题筛选 400；`pytest` 112 | **通过** |
| E6 侧边栏默认收起 | 首次 78px（收起）→ 展开 264px → 刷新保持展开 → 清存储再刷新回收起 | **通过** |
| E7 门禁 | `pytest` **112 passed**、`smoke` **PASS 40/40**、`tsc` exit 0、`build` exit 0 | **通过** |
| E13 箭头更大 + 两支 | 2 支、30px（令牌）、不压 stats、错峰动效、reduced-motion 关闭 | **通过** |
| E14 收起态用户按钮 | 点击后 `collapsed=false` + `.side-pop` 出现 + `aria-expanded=true`；`Esc` 关闭 | **通过** |
| E15 满员加入体验 | 满员卡片按钮「已满」且禁用；满员 + 待批 → 房主批准 **409 ROOM_FULL**、等待室显示「房主现在无法批准」；满员 + 新人直接申请 → 留在首页、待批 0（r005 成立） | **通过** |

## 2. 规则核对（AGENTS.md）

| 规则 | 核对 | 结论 |
| --- | --- | --- |
| 未批不实现；改动挂 `rNNN` | 需求单 §2 有你的批复回读；提交信息带 `[Req: r007]` | **通过** |
| 一次提交一个逻辑增量 | cp-0 / cp-1+4 / cp-3 / cp-2 / cp-5 共 5 个提交 | **通过** |
| 零新依赖、不改端口 | `package.json` 与后端依赖零变化；8000/5173 不变 | **通过** |
| 不改历史迁移文件 | 新增 `006_…`，未动 001~005 | **通过** |
| 文档与代码同提交 | 每个 cp 提交都带文档 | **通过** |
| 行为变更记 ADR | 本轮为界面口径回退与控件替换（r004 ADR-0015 的工具栏位置被回退 → 在本页与实现页登记，未新增 ADR，属「按用户批复回退既有决定」） | **通过**（如你要独立 ADR，说一声我补） |

## 3. 文档对账

| 项 | 结论 |
| --- | --- |
| 模块轴 | 实现页 `02-modules/r007-topic-and-scrollhint.md`、功能页 `…-features.md` | **齐** |
| 轮次轴 | `rounds/r007-topic-and-scrollhint/{redirect-01,design,changes,review}.md` | **齐**（review 定稿） |
| 索引 | 需求索引行、模块 README、docs/README、roadmap §9 均已回填 | **齐** |

## 4. 视觉对账

| 组 | 方式 | 结果 |
| --- | --- | --- |
| 箭头 | 截图 `r007-firstscreen-1440x900.png` / `…-1258x566.png` | 低对比居中，不压 stats 与工具栏 |
| 主题下拉 | 截图 `r007-topic-select.png` | 暗色面板 + 图标 + 选中态，与既有材质一致 |
| 主题卡片 | 截图 `r007-topic-cards{,-selected}.png` | 图标 + 名称 + 用途三层，选中描边/角标 |
| 侧边栏 | 截图 `r007-sidebar-collapsed.png` | 78px 图标窄栏 |
| 零 emoji / 单一图标库 | 扫描 | 仅 Lucide（14 只主题图标 + `ChevronDown`/`Check`） |
| 动效降级 | reduced-motion 复测 | 箭头与面板动效均关闭 |

## 5. 两栏处置清单

**已落地可保留**

1. 工具栏回到 hero 下方（按你的要求回退 r004 cp-3 的位置），hero 未压缩。
2. 风格化浮动下箭头（纯装饰、不可点、可调令牌、降级关闭）。
3. 主题控件全部风格化：首页自绘下拉 + 创建房间卡片（含 14 只 Lucide 图标与用途文案）。
4. 主题扩容到 14 项（少 AI、补哲学/历史/数学），迁移 006 + 三处白名单 + 用例保证一致。
5. 侧边栏默认收起并可记住选择。

**未闭合项 / 如实说明**

| # | 项 | 状态 |
| --- | --- | --- |
| 1 | 房间列表仍在首屏外 | 你选的「不加」压 hero；要进首屏随时可压（令牌现成） |
| 1b | 满员时**已在等待室**的申请不会被自动处理 | 你反馈的「不能申请但会进入等待间」实测对应这一条：房主批准会被容量挡回 409，申请人原本无提示 → 已加等待室说明 + 撤回入口（撤回按钮原本就有）。**是否要在房间满员时自动把待批申请置为「已拒绝」并通知**：属语义变更，等你一句话（默认不做） |
| 2 | r006 未合并 | 本轮分支自 r006 拉出，**建议先合 r006 再合 r007**（`round-r006-done` → `round-r007-done`） |
| 3 | 主题二级分类 / 主题图标自定义 | 不做 |
| 4 | 存量房间的旧 `topic_label` | 不受影响（白名单只约束 `topic` 值） |

## 6. 合并指引（由人执行）

```bash
git checkout main
git merge --no-ff req/r007-topic-and-scrollhint   # 建议先合 req/r006-ui-sync-polish
git tag -a round-r007-done -m "r007 完成（首屏引导 + 主题控件与扩容 + 侧边栏默认收起）"
```

合并后复验：`pytest backend/tests -q` → `python backend/scripts/smoke.py` → `cd frontend && npx tsc --noEmit && npm run build`。
