---
title: r007 变更台账
description: cp 台账、文件台账、门禁记录与实测证据。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
验收对照见 `review.md`。

## 1. cp 台账

| cp | 内容 | 状态 | 提交 | 证据 |
| --- | --- | --- | --- | --- |
| cp-r007-0 | 阶段 1 文档（需求单 / design / 台账骨架 / 索引与 roadmap 回填） | in_progress | — | —— |
| cp-r007-1 | 工具栏换回 hero 下方 + 浮动下箭头 | **完成 2026-09-19** | 见 cp-1 提交 | E1/E2 实测（§3.1） |
| cp-r007-2 | 主题控件风格化（自绘下拉 + 创建房间卡片） | **完成 2026-09-19** | 见 cp-2 提交 | E3/E4 实测（§3.4） |
| cp-r007-3 | 主题扩容（迁移 006 + 前后端白名单 + 用例） | **完成 2026-09-19** | 见 cp-3 提交 | E5 实测（§3.3） |
| cp-r007-4 | 侧边栏默认收起（含记住选择） | **完成 2026-09-19** | 见 cp-4 提交 | E6 实测（§3.2） |
| cp-r007-5 | 收官（真机取证 / 门禁 / 文档 / review） | **完成 2026-09-19** | 见 cp-5 提交 | E7 通过（§4） |

## 2. 文件台账

| 文件 | 改什么 | 状态 |
| --- | --- | --- |
| `docs/00-requirements/r007-topic-and-scrollhint.md`（新） | 需求/口径回读/主题清单/E1~E7 | landed（cp-0） |
| `docs/rounds/r007-topic-and-scrollhint/{design,changes,review}.md` | 设计 / 台账 / 审查 | landed（cp-0，review 待定稿） |

## 3. 实测证据

### 3.1 cp-1（E1/E2）

| 视口 | hero | 工具栏 | 工具栏−hero 底 | 房间列表首行 | 箭头 |
| --- | --- | --- | --- | --- | --- |
| 1440×900 | 101 → 801 | **841 → 886**（回到 hero 之下、首屏内） | **40px**（区块间距） | 910 | 存在，`pointer-events: none`、`aria-hidden=true`、无 `onclick`、`animation: scroll-hint-bob` |
| 1258×566 | 101 → 599 | **639 → 684**（换回原位，首屏外） | **40px** | 708 | 同上 |

- 工具栏确实回到 hero 下方（间隔 40px = 一个区块间距），不再"插在 hero 之上"；`prefers-reduced-motion` 下箭头浮动被显式关闭（`.scroll-hint { animation: none; }`）。
- 箭头为纯装饰：`role="presentation"`、`aria-hidden`、无点击、不进 tab 序。

### 3.2 cp-4（E6）

| 步骤 | 实测 |
| --- | --- |
| 首次加载（无 localStorage） | `aside.sidebar.collapsed` = **true**，宽 **78px**（只留图标列） |
| 点「展开侧边栏」 | `collapsed` = false，宽 **264px** |
| 刷新页面 | 仍为展开（**记住选择** ✓） |
| 清掉 `lg.sidebar.collapsed` 再刷新 | 回到收起 ✓ |

### 3.3 cp-3（E5 主题扩容）

- 迁移 `006_r007_topic_taxonomy.sql` 应用成功：`db_init` 输出 `[migrate] … 006_r007_topic_taxonomy`，`schema_migrations = 6`。
- 三处白名单一致（14 项、顺序相同：原有 3 项在前、`custom` 最后）：`schemas/rooms.py` 的 `TopicLiteral`/`TOPICS`、`api/rooms.ts` 的 `Topic`/`TOPIC_OPTIONS`。
- 用例 `test_new_topic_accepted_and_invalid_topic_rejected`：新主题 `philosophy-history` 建房 **201**；非法主题 `quantum-cooking` 建房 **400**；筛选未知主题 **400**。
- 门禁：`pytest` **112 passed**。

### 3.4 cp-2（E3/E4 主题控件风格化）

| 断言 | 实测（Playwright，1440×900） |
| --- | --- |
| 原生下拉已移除 | 首页 `select` 数量 **0**；`.topic-select-btn` 存在，文案「全部主题」 |
| 面板语义 | 展开后 `role="listbox"`、`aria-expanded=true`、**15 项**（全部主题 + 14 主题）、**14 项带 Lucide 图标** |
| 项标签与顺序 | 全部主题 / 伊壁鸠鲁主义 / 数理生物学 / 德国史模拟 / 西方哲学史 / 中国哲学 / 伦理学 / 世界近代史 / 中国古代史 / 数学分析 / 线性代数 / 概率论与数理统计 / 数论 / 机器学习基础 / 自定义 |
| 键盘 | `↓↓` 高亮移到「数理生物学」→ `Enter` 选中，按钮文案随之变化、面板关闭；`Esc` 关闭并把焦点还给按钮；点击外部关闭 |
| 创建房间卡片 | `.topic-card` **14 张**，**全部带图标 + 一句用途**（首张「伊壁鸠鲁主义 \| 从欲望清单到快乐主义」）；默认选中第一张；点「线性代数」→ `aria-checked=true` 唯一切换 |
| 截图 | `r007-topic-select.png`、`r007-topic-cards.png`、`r007-topic-cards-selected.png`（`%TEMP%\lg_r007\`） |

> 实现坑（cp-2 首轮实测抓到）：键盘处理原挂在**面板**上，而焦点始终在按钮 → `↓` 只改高亮、`Enter` 不生效。改为把 `onKeyDown` 挂在根容器（按钮与面板都冒泡到它）后正常。

## 4. 门禁记录

| 时点 | pytest | smoke | tsc | build |
| --- | --- | --- | --- | --- |
| cp-0 | 111 passed（r006 基线） | —— | exit 0 | exit 0 |
| cp-3 后 | 112 passed（+主题用例） | —— | —— | —— |
| **收官** | **112 passed** | **PASS 40/40** | exit 0 | exit 0 |

### 4.1 cp-5（收官）

- 真机取证（Playwright）：首页首屏两档截图、主题下拉展开截图、主题卡片选中截图、侧边栏收起截图（`%TEMP%\lg_r007\`）。
- 文档：实现页 + 功能页（F-32~F-36）、review 定稿（E1~E7 与规则/文档/视觉对账、两栏清单）、索引与 roadmap 回填。
- `pytest` **112 passed** / `smoke` **PASS 40/40** / `tsc` + `build` exit 0。
