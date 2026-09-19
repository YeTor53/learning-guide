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
| cp-r007-2 | 主题控件风格化（自绘下拉 + 创建房间卡片） | planned | — | E3/E4 |
| cp-r007-3 | 主题扩容（迁移 006 + 前后端白名单 + 用例） | **完成 2026-09-19** | 见 cp-3 提交 | E5 实测（§3.3） |
| cp-r007-4 | 侧边栏默认收起（含记住选择） | **完成 2026-09-19** | 见 cp-4 提交 | E6 实测（§3.2） |
| cp-r007-5 | 收官（真机取证 / 门禁 / 文档 / review） | planned | — | E7 |

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
