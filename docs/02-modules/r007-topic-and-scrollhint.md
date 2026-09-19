---
title: r007 实现页：布局回退、滚动提示、主题控件与扩容、侧边栏默认收起
description: 决定性事实源——工具栏位置、箭头令牌、主题控件状态机、迁移 006 与三处白名单、侧边栏持久化；含实测数字与踩坑。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
需求与验收见 `docs/00-requirements/r007-topic-and-scrollhint.md`；设计与实测表见 `docs/rounds/r007-topic-and-scrollhint/{design,changes,review}.md`。

## 1. 工具栏位置（回到 hero 之后）

- `pages/RoomsPage.tsx`：`.toolbar` 整块位于 `<section className="hero">` **之后**（r004 cp-3 曾把它移到 hero 之前）；实测 hero 底与工具栏间距 **40px**（= 一个区块间距）。
- hero 的 `min-height` / 间距**未改**（Q6「不加」）→ 1440×900 工具栏在首屏内（841→886），1258×566 在首屏外（639，与 r004 之前一致），房间列表首行在 910。

## 2. 向下提示箭头（`components/ScrollHint.tsx`）

- hero 底缘居中；**纯装饰**：`role="presentation"`、`aria-hidden`、`pointer-events: none`、无 `onClick`、不进 tab 序（Q2=2「只浮动不可点」）。
- 令牌（单点可调）：`--scroll-hint-bottom: 10px`、`--scroll-hint-travel: 6px`、`--scroll-hint-duration: 1.9s`；`@keyframes scroll-hint-bob`。
- 降级：最后一处 `@media (prefers-reduced-motion: reduce)` 显式 `.scroll-hint { animation: none; }`（**注意**：文件里有多处 reduced-motion 块，只有最后一处能压住本规则）。

## 3. 主题控件（`TopicSelect` / `TopicPicker` / `topicIcons`）

| 组件 | 用在哪 | 要点 |
| --- | --- | --- |
| `TopicSelect` | 首页筛选 | 自绘 listbox：按钮（当前项 + 图标 + 折角）+ 面板（`role="listbox"`，`role="option"` + `aria-selected`）；点击开合、`Esc` 关闭并回焦、点外关闭、`↑/↓` 移动、`Enter/Space` 选中 |
| `TopicPicker` | 创建房间 | 14 张卡片（`role="radiogroup"` / `role="radio"` + `aria-checked`）：图标 + 主题名 + 一句用途；选中描边 + 角标 |
| `topicIcons.tsx` | 两者共用 | `Topic → LucideIcon`；**放 UI 层**（`api/rooms.ts` 是契约层，不引 React 组件） |

- 坑：键盘处理必须挂在**根容器**（按钮与面板都冒泡到它）。挂在面板上时焦点仍在按钮 → `↓` 只改高亮、`Enter` 不生效（cp-2 首轮实测）。

## 4. 主题扩容（迁移 006 + 三处白名单）

- 迁移 `db/sql/006_r007_topic_taxonomy.sql`：`DROP CONSTRAINT IF EXISTS rooms_topic_check` + 重建（**不改历史迁移文件**；不写 BEGIN/COMMIT，与 004/005 一致）。应用后 `schema_migrations = 6`。
- 白名单**三处同步**（顺序即展示顺序，前 3 项为保留的原有主题、`custom` 最后）：`schemas/rooms.py`（`TopicLiteral`/`TOPICS`）、`api/rooms.ts`（`Topic`/`TOPIC_OPTIONS`）、`api/routers/rooms.py`（筛选校验沿用 `TOPICS`，逻辑未改）。
- 14 项：伊壁鸠鲁主义 / 数理生物学 / 德国史模拟 / 西方哲学史 / 中国哲学 / 伦理学 / 世界近代史 / 中国古代史 / 数学分析 / 线性代数 / 概率论与数理统计 / 数论 / 机器学习基础 / 自定义。
- **坑**：用「第一个 `]`」截取旧数组会把类型注解的 `]` 当成数组结尾 → 替换后残留旧数组、`tsc` 报 `string not assignable to Topic`。截取数组要按 `] = [` 或整段函数定位。

## 5. 侧边栏默认收起（`App.tsx`）

- 首次访问（无 `localStorage['lg.sidebar.collapsed']`）→ `collapsed = true`（实测宽 **78px**，只留图标列）。
- 切换时写入存储；刷新后保持（实测展开态 264px 刷新仍在）；清掉存储再刷新回到收起。
- 窄屏（`max-width: 900px`）横向条形态不变（`narrowStrip` 强制展开、隐藏折叠按钮）。

## 6. 验证数字（2026-09-19）

| 项 | 结果 |
| --- | --- |
| 工具栏 | 1440×900：841→886（hero 之后 40px、首屏内）；1258×566：639（回到原位） |
| 箭头 | 存在且 `pointer-events:none`、`aria-hidden`、无点击；reduced-motion 下 `animation: none` |
| 首页主题控件 | 原生 `select` **0**；面板 15 项、14 项带图标；`↓↓`+`Enter` 选中「数理生物学」；`Esc` 回焦 |
| 创建房间卡片 | 14 张全部带图标 + 用途；点选切换 `aria-checked` |
| 主题白名单 | `db_init` 应用 `006_r007_topic_taxonomy`、`schema_migrations=6`；新主题建房 201、非法主题 400 |
| 侧边栏 | 首次 78px 收起 → 展开 264px → 刷新保持 → 清存储回收起 |
| 门禁 | `pytest` **112 passed** / `smoke` **PASS 40/40** / `tsc` + `build` exit 0 |

## 7. 遗留

1. 房间列表仍在首屏下方（你选了「不加」压 hero）—— 靠箭头与滚动引导；哪天真要进首屏，压 hero 与收间距是现成的手（令牌都在）。
2. 主题没有二级分类/描述页；卡片上的「一句用途」写在 `TOPIC_OPTIONS.hint`（改文案只动一处）。
3. 演示库里历史房间的 `topic_label` 仍是旧值（主题白名单扩容不影响存量数据）。
