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
| cp-r007-6 | 追加：箭头更大且两支 / 收起态用户按钮有反应 / 满员加入体验 | **完成 2026-09-19** | 见 cp-6 提交 | E13~E15（§3.5） |
| cp-r007-7 | 修「什么申请都撤回不了」+ 抽屉名言移除 + 刷新反馈 | **完成 2026-09-19** | 见 cp-7 提交 | E16~E18（§3.6） |
| cp-r007-8 | 追加需求：往下划隐藏顶栏 | **完成 2026-09-19** | 见 cp-8 提交 | E19（§3.7） |

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

### 3.5 cp-6（E13~E15，你 2026-09-19 的三条反馈）

| 断言 | 实测（Playwright 1440×900） |
| --- | --- |
| 箭头两支 | `.scroll-hint svg` = **2** 支；尺寸 = **45px**（`--scroll-hint-size`，30px × 150%，2026-09-19 再放大）；幅度 14px、叠压 −9px；`pointer-events: none`；1440×900 下箭头区间 714→795 在 hero 底（801）内且**不压 `stats`、不压工具栏**；1258×566 同样不压 |
| 箭头动效 | `animation-name: scroll-hint-bob`；两支错峰（第二支延后半周期）；`prefers-reduced-motion` 下 `animation: none` |
| 收起态用户按钮 | 首次加载 `collapsed=true`；**点击** `.side-user-btn` → `collapsed=false`（侧边栏展开，78→264px）**且** `.side-pop` 出现、`aria-expanded=true`；`Esc` 关闭 |
| 满员卡片 | 满员房间卡片主按钮 = 「**已满**」、`disabled=true`、`title="本场名额已满（在册成员 8/8，等于上限）"`；未满房间仍是「申请加入」 |
| 满员 + 待批 | 申请人先申请（在等待室）→ 房主把房间填到 **8/8** → ① 房主批准该申请 → **HTTP 409 `ROOM_FULL`**（r005 不变量成立）；② 申请人等待室出现「**房间已满（在册 8/8，等于上限），房主现在无法批准**；你可以撤回申请，或先去看看别的房间。」 |
| 满员 + 新人直接申请 | 新人点「申请加入」（旧行为）→ 实测**留在首页**、卡片下显示「房间已满（上限 8 人）」、房主待批条数仍为 **0**（= r005「满员直接拒、不进等待室」成立）；现在按钮已改为禁用，连点击入口都没有了 |
| 截图 | `r007-hint-two.png`、`r007-user-btn-collapsed-click.png`、`full-room-card.png`、`wait-after-full.png` |

### 3.6 cp-7（E16~E18，你 2026-09-19 的三条反馈）

| 断言 | 实测 |
| --- | --- |
| **撤回不了（根因）** | 旧路径 `GET /api/rooms/{id}/join-requests`（管理权限接口）以申请人身份调用 → **403 FORBIDDEN**（实测返回 `{"code":"FORBIDDEN","message":"你没有该操作的权限"}`）→ 前端 `.catch(()=>[])` 得到空列表 → 一律抛「找不到待批申请」。 |
| 撤回（修后） | 房间详情给本人带上 `myRequestId`（实测 `pending` 时 = `req_…`，撤回后为 `null`）；点「撤回申请」→ `POST /api/join-requests/req_…/withdraw` **200**，页面切到「这个房间还需要先申请」+「重新申请」；房主视角 `myRequestId` 为 `null`。用例 `test_detail_exposes_my_request_id_for_applicant`，`pytest` **113 passed**。 |
| 抽屉名言移除 | 交流页：成员抽屉 `.quote-line` = **0**、讨论抽屉 = **0**（等待室/首页的名言保留）。 |
| 刷新反馈 | 点「刷新」后列表 DOM **重新挂载**（`gridSame=false`、`cardSame=false`，20 张卡）→ 卡片内元素的 `rise` 入场动画按 `--i*40ms` 重放（`.stagger > *`）。**如实**：卡片元素本身没有动画，动的是它的子元素，所以量 `card.getAnimations()` 会是空数组 —— 观感上是整列表重新浮入一次。 |

### 3.7 cp-8（E19，追加需求：往下划隐藏顶栏）

| 步骤 | 实测（1440×900） |
| --- | --- |
| 页顶初始 | `.topbar` `top=0 / bottom=61`、无 `topbar-hidden`、`transform: none` |
| 向下滚 300px | `topbar-hidden` 出现、`top=-61 / bottom=0`、`transform: translateY(-61px)`、品牌 `pointer-events: none` |
| 再向下滚 300px | 仍隐藏 |
| 向上滚 200px | 顶栏回来（`top=0`） |
| 回到顶部 | 回来 |

实现：`hooks/useHideOnScroll.ts`（阈值 4px、rAF 合并滚动事件、只读 `scrollY`）+ `.topbar` 加 `transition: transform var(--t-base) var(--ease)` + `.topbar-hidden { transform: translateY(-100%) }`。
口径假设：**向下划隐藏 / 向上划或回顶部显示**（你只说了「往下划隐藏」这一半，回来这半按通用做法定；要改成别的说一声）。
