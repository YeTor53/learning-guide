---
title: r007 设计：布局回退、滚动引导、主题控件与扩容、侧边栏默认收起
description: 逐文件函数级设计（含动效令牌、下拉组件状态机、迁移 006 写法、侧边栏持久化）。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
需求与验收见 `docs/00-requirements/r007-topic-and-scrollhint.md`；实测证据见 `redirect-01.md`。

## 1. 改动面

| 面 | 文件 | 一句话 |
| --- | --- | --- |
| ① 工具栏回退 | `pages/RoomsPage.tsx` | `.toolbar` 从 `<section className="hero">` **之前**移到**之后**（回到 r004 cp-3 之前的位置） |
| ② 浮动下箭头 | `components/ScrollHint.tsx`（新）+ `global.css` | hero 底缘居中，纯装饰、不可点、`pointer-events: none`；浮动用令牌化动效 |
| ③ 首页主题下拉 | `components/TopicSelect.tsx`（新）+ `pages/RoomsPage.tsx` | 自绘 listbox：按钮 + 面板 + 图标 + 选中态 + 键盘/Esc/点外关闭 |
| ④ 创建房间主题卡片 | `components/TopicPicker.tsx`（新）+ `components/RoomForm.tsx` | 卡片组：图标 + 主题名 + 一句用途；`aria-pressed` |
| ⑤ 主题扩容 | `db/sql/006_r007_topic_taxonomy.sql`（新）、`schemas/rooms.py`、`api/rooms.ts`、`api/rooms.py` 路由校验、用例 | 三处白名单同步 + 迁移重建 CHECK |
| ⑥ 侧边栏默认收起 | `App.tsx` | 首次 `collapsed=true`；切换写入 localStorage；窄屏横向条不变 |

## 2. ① 工具栏回退（`RoomsPage.tsx`）

把现有 `<div className="toolbar">…</div>` 整块（含状态 tabs、主题下拉、只看我的、刷新、创建房间）**移到 hero 之后**；hero 的 `min-height` / 间距**一律不改**（Q6「不加」）。
量测口径（E1）：`toolbar.top > hero.bottom`，间距 = `toolbar.top - hero.bottom`（预期等于区块间距）。

## 3. ② 浮动下箭头（`ScrollHint.tsx`）

```tsx
export default function ScrollHint() {
  return (
    <div className="scroll-hint" role="presentation" aria-hidden>
      <ChevronDown size={20} strokeWidth={1.5} />
    </div>
  )
}
```

- 定位：`.hero` 内绝对定位，`left: 50%; translateX(-50%)`，`bottom: var(--scroll-hint-bottom)`（默认 12px，单点可调）。
- **不可点**（Q2=2）：`pointer-events: none`，不绑 onClick，不进 tab 序。
- 动效：`--scroll-hint-travel`（默认 6px）+ `--scroll-hint-duration`（默认 1.8s）+ `--ease`；`@keyframes scroll-hint-bob`；`prefers-reduced-motion: reduce` 时 `animation: none`。
- 层次：低对比（`color: var(--text-mute)`，`opacity` 0.7），避免与 stats/工具栏争夺注意力。
- 位置校验：不与 `.thinker-box`、`.stats` 重叠（`.hero-inner` 有内边距；箭头落在 hero 底缘留白里）。

## 4. ③ 首页主题下拉（`TopicSelect.tsx`）

```ts
interface Props {
  value: Topic | ''
  options: { value: Topic; label: string; icon: LucideIcon; hint: string }[]
  onChange: (value: Topic | '') => void
  allLabel?: string          // 默认「全部主题」
  disabled?: boolean
}
```

- 结构：`<button aria-haspopup="listbox" aria-expanded>` + 面板 `role="listbox"`，每项 `role="option"` + `aria-selected`，列表项含 `Icon`。
- 交互状态机：点击按钮开/关；`Esc` 关并把焦点还给按钮；点击面板外关（`pointerdown` + `contains` 判断）；`ArrowDown/ArrowUp` 移动高亮、`Enter` 选中；打开时聚焦当前选中项。
- 呈现：复用既有令牌（`.select` 的暗色底、`--line` 描边、`--r-md` 圆角）；面板 `--ink-800` 底 + `--sh` 阴影；选中项 `--accent-soft` 底 + `--accent` 文字。
- 无障碍：`aria-label="主题筛选"`；不用原生 `select`（E3 断言 `select` 计数为 0）。

## 5. ④ 创建房间主题卡片（`TopicPicker.tsx`）

- 卡片：`<button type="button" aria-pressed>`，内含图标 + 主题名 + `hint`（一句话用途，如「西方哲学史 · 从苏格拉底到康德」）。
- 网格：`repeat(auto-fill, minmax(150px, 1fr))`，窄屏自动折行；选中态 `--accent` 描边 + `--accent-soft` 底 + 左上勾选角标。
- `RoomForm` 接入：`<TopicPicker value={topic} onChange={pickTopic} />`；选中 `custom` 仍显示「主题名」输入框（行为不变）。

## 6. ⑤ 主题扩容

- 迁移 `006_r007_topic_taxonomy.sql`（**不写 BEGIN/COMMIT**，与 004/005 一致；`migrate.split_statements` 已支持）：

```sql
ALTER TABLE rooms DROP CONSTRAINT IF EXISTS rooms_topic_check;
ALTER TABLE rooms ADD CONSTRAINT rooms_topic_check CHECK (topic IN (
  'epicureanism','math-biology','german-history',
  'philosophy-history','chinese-philosophy','ethics',
  'modern-history','ancient-china',
  'mathematical-analysis','linear-algebra','probability-statistics','number-theory',
  'machine-learning','custom'
));
```

- 三处同步：`schemas/rooms.py`（`TopicLiteral` + `TOPICS`）、`api/rooms.ts`（`Topic` + `TOPIC_OPTIONS` 含 `icon`/`hint`）、`api/routers/rooms.py`（筛选参数校验沿用 `TOPICS`，无需改逻辑）。
- 用例：`test_rooms_api.py` 增「用新主题建房 201」「非法主题 400」；`test_schema.py` 迁移清单加 `006_…`。
- 文档：模块页 DDL 段（`r001-rooms.md` 的那行 CHECK）追加指路行（不改历史正文的其它内容）。

## 7. ⑥ 侧边栏默认收起（`App.tsx`）

```ts
const SIDEBAR_KEY = 'lg.sidebar.collapsed'
const [collapsed, setCollapsed] = useState<boolean>(() => {
  try {
    const saved = localStorage.getItem(SIDEBAR_KEY)
    return saved === null ? true : saved === '1'   // 首次访问默认收起
  } catch { return true }
})
```

- 切换时写回 `localStorage`；窄屏（`narrowStrip`）仍强制展开并隐藏折叠按钮（`SideBar` 逻辑不变）。
- 收起态下 `SideBar` 只渲染图标列（现有行为）；`aria-label` 与 tooltip 已有。

## 8. 验收映射

| 验收 | 证据 |
| --- | --- |
| E1 | `toolbar.top` vs `hero.bottom`（1440×900、1258×566 两档） |
| E2 | `role="presentation"`、`pointer-events:none`、reduced-motion 后 `animation-name:none`、截图 |
| E3/E4 | DOM 断言（`select`=0、`aria-expanded`、`aria-pressed`）+ 键盘 Tab/Enter/Esc 实测 + 截图 |
| E5 | `pytest` 新用例 + 真实 HTTP（新主题建房 201 / 非法 400）+ `db_init` 输出 `006_…` |
| E6 | 清空 localStorage 后首次加载 `collapsed=true`；展开→刷新仍展开；900px 窄屏仍为横向条 |
| E7 | 四条门禁命令 |

## 9. 非目标

不做主题的二级分类/标签云；不做主题图标的自定义上传；不改房间卡与交流页的主题呈现（已风格化）；不动 hero 高度（Q6「不加」）；不给箭头加文字或点击行为（Q2=2）。

## 10. 变更记录

| 日期 | 版本 | 改了什么 | 依据 |
| --- | --- | --- | --- |
| 2026-09-19 | cp-0 | 建页：六个改动面的函数级设计与验收映射 | 你的批复（`1 2 1 1 1` + 工具栏换回 + 侧边栏默认收起 + 「不加」） |

## 11. 追加（cp-6，2026-09-19 你的三条反馈）

| 项 | 改法 |
| --- | --- |
| **箭头更大 + 两支** | `ScrollHint` 渲染两组 `ChevronDown`；尺寸走 CSS 令牌 `--scroll-hint-size`（默认 **30px**，作用于 `svg` 的 `width/height`，与组件的 `size` 解耦）；两支错峰：第二支 `animation-delay: calc(var(--scroll-hint-duration) / 2 * -1)` + `opacity: .55`；浮动幅度 `--scroll-hint-travel` 9px、周期 `--scroll-hint-duration` 2s。**坑**：flex 的 `gap` **不接受负值**（会退回 `normal`，实测两支贴不上）→ 叠压改用 `--scroll-hint-gap` 走 `margin-top`（默认 −6px）。 |
| **收起态用户按钮「点了没反应」** | 根因：`SidebarUserCard` 的浮窗条件是 `open && !collapsed`，收起时 `onClick` 只切内部 `open` → 什么也不显示，但按钮仍有 focus 环。改法：`activate()` —— 收起态时 `onExpand()`（由 `SideBar` 传 `onToggleCollapsed`）**先展开侧边栏**再打开浮窗；`onFocus` 只在展开态且 `:focus-visible` 时打开（Tab 经过不会突然改布局）。 |
| **满员时的加入体验** | ① `RoomCard`：`full` 时主按钮改成**禁用的「已满」**（`title` 写明「在册 N/N = 上限」），不再「点了才报错」；② `WaitingPage`：`pending && room.memberCount >= room.capacity` 时显示「房间已满（在册 N/N，等于上限），房主现在无法批准；你可以撤回申请，或先去看看别的房间。」（满员批准会被 r005 的容量不变量挡回 409，这条把原因讲出来） |
