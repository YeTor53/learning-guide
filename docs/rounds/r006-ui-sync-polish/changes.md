---
title: r006 变更台账
description: 逐文件改动、每 cp 的实测证据与文档产出对账。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
验收对照见 `review.md`；函数级设计见 `design.md`。

## 1. cp 台账

| cp | 内容 | 状态 | 提交 | 证据 |
| --- | --- | --- | --- | --- |
| cp-r006-0 | 阶段 1 文档先行（需求单 / design / ADR-0017 / 台账骨架 / 索引与 roadmap 回填） | in_progress | — | —— |
| cp-r006-1 | 麦徽标改真实麦克风状态（静音事件驱动重渲染） | **完成 2026-09-19** | 见 cp-1 提交 | E1/E2 双浏览器实测通过（§4.1） |
| cp-r006-2 | `lg.roster` 同步 + 三个刷新触发点 | planned | — | E3/E4/E5 |
| cp-r006-3 | 个人信息浮窗 + 哲学语句池 | **完成 2026-09-19** | 见 cp-3 提交 | E6/E7 实测通过（§3.3） |
| cp-r006-4 | 图版初始位置下移 + 前端优化清点处置 | **完成 2026-09-19** | 见 cp-4 提交 | E8 实测下移 50px / 竖屏 46px；E9 复核 0 处原生弹窗（§3.4） |
| cp-r006-5 | 收官（门禁 / r004 欠账 / 文档回填 / review 定稿） | planned | — | E10 |

## 2. 文件台账

| 文件 | 模块 | 改什么 | 落地文档 | 状态 |
| --- | --- | --- | --- | --- |
| `docs/00-requirements/r006-ui-sync-polish.md`（新） | 契约 | 需求/口径回读/验收/cp | 自身 | landed（cp-0） |
| `docs/rounds/r006-ui-sync-polish/{design,changes,review}.md` | 契约 | 函数级设计 / 台账 / 审查 | 自身 | landed（cp-0，review 待定稿） |
| `docs/03-decisions/r006-adr-0017-ui-polish-decisions.md`（新） | 决策 | D1~D4 界面口径 | 自身 | landed（cp-0） |
| `docs/rounds/r006-ui-sync-polish/redirect-01.md` | 契约 | 两例实测 + 定性（原 r006-fix-mic-badge 目录改名而来） | 自身 | landed（改名） |
| `frontend/src/hooks/useMicStates.ts`（新） | 前端 | `identity → isMicrophoneEnabled` 状态表 + 10 个静音/轨道事件订阅 | design §2 | landed（cp-1） |
| `frontend/src/components/live/ParticipantTile.tsx` | 前端 | 麦徽标改由 `micMuted` 驱动（静音才显示、只图标 + title）；删掉挂在 `!showVideo` 上的旧图标 | design §2 | landed（cp-1） |
| `frontend/src/components/live/LiveStage.tsx`、`pages/RoomLivePage.tsx`、`styles/global.css` | 前端 | 接 `micStates` 并逐格传 `micMuted`；`.live-tile-mic` 样式 | design §2 | landed（cp-1） |
| `frontend/src/hooks/useDataChannel.ts`、`hooks/useRosterSync.ts`（新）、`pages/RoomLivePage.tsx` | 前端 | `lg.roster` topic + 广播/接收 + 聚焦·可见性·进房重连·30 秒兜底四个刷新触发点；5 处房间动作补广播 | design §3 | landed（cp-2） |
| `frontend/src/data/philosophy.ts`（新） | 前端 | 12 条真实语录 + `pickDailyQuote()`（UTC+8 年内天数取模） | design §5 | landed（cp-3） |
| `frontend/src/components/SidebarUserCard.tsx`（新）、`SideBar.tsx` | 前端 | 紧凑入口（头像+名字）+ 点击/键盘 focus 展开浮窗（Esc/点击外部关闭）+ 引文/加入日期/登出 | design §4 | landed（cp-3） |
| `frontend/src/styles/global.css` | 前端 | `.side-user-btn`/`.side-pop*` 样式 + 窄屏向下弹 + reduced-motion；`--thinker-top` -110px → -60px（窄屏 -92px → -46px） | design §4/§6 | landed（cp-3/cp-4） |

## 3. 实测证据

### 3.1 cp-1（麦徽标，双浏览器真机）

房间 `麦标取证2`（A=麦主、B=听众，两人都没开摄像头）：

| 步骤 | B 侧看到的格子 | B 端 SDK |
| --- | --- | --- |
| A 未静音 | A 的格子**无**麦徽标（B 自己也无） | `remote: [["麦主", true]]` |
| A 点静音 | A 的格子**出现**麦徽标（`title="麦克风已静音"`） | `remote: [["麦主", false]]` |
| A 取消静音 | 徽标**消失** | —— |
| 反向：B 静音 | **A 侧** B 的格子出现麦徽标 | —— |

即：徽标只跟麦克风状态走，与「有没有摄像头」无关（E1/E2 通过）。

### 3.2 cp-2（两端同步，双浏览器真机）

| 场景 | 改前（r005） | 改后（cp-2） |
| --- | --- | --- |
| A（房主）在界面批准第三人 → B 端状态条 | 5 秒后仍 `2 / 8`（只有 F5 才变） | **0.23~0.46 秒**变 `3 / 8`（E3 通过） |
| A 在界面批准 → B（协管）待批徽标 | 靠既有 5 秒轮询 | **1.46 秒**清空（E4 通过；原口径 5 秒） |
| B 端窗口聚焦（纯 API 改库、无广播） | 不刷新 | **0.22 秒**拉到新值（关键时刻触发通过） |
| 纯 API 改库（无任何端广播）+ B 不聚焦不刷新 | —— | **9.8 秒**由 30 秒兜底轮询拉平（E5 通过；耗时取决于轮询相位） |

> 说明：`待批` 本来就是 5 秒轮询（`requestsQuery.refetchInterval`），本次把它拉进秒级广播；**人数**此前完全无刷新（只有本端动作 + F5）。

## 4. 门禁记录

| 时点 | pytest | smoke | tsc | build |
| --- | --- | --- | --- | --- |
| cp-0 | 111 passed（r005 基线） | 40/40 | exit 0 | exit 0 |

### 3.3 cp-3（个人信息浮窗 + 哲学语句）

| 断言 | 实测（Playwright，1440×900） |
| --- | --- |
| 默认不展示账号信息 | 侧边栏底部文本 = `个人信息 | 浮 | 浮窗测试 | 收起侧边栏`（头像首字 + 名字，无邮箱/id/日期），`.side-pop` 不存在、`aria-expanded=false` |
| 点击展开 | `.side-pop` 出现且 `role="dialog"`、`aria-expanded=true`；内容 = 名字 / 邮箱 / **「在隆冬，我终于知道，我身上有一个不可战胜的夏天。 —— 加缪」** / 加入于 2026/9/19 / 登出 |
| 键盘 focus 展开 | 从「收起侧边栏」按 `Shift+Tab` → `activeElement=side-user-btn`，浮窗自动出现（`:focus-visible` 判定） |
| 关闭 | `Esc` → 关闭；点击浮窗外部 → 关闭 |
| 语录稳定 | 刷新页面后再读同一句（同日固定） |
| 窄屏（900×1000） | 浮窗改为**向下**弹：`popTop=150 / popBottom=399 / vh=1000` → 完整在视口内 |

> 实测踩到一个真 bug 并修掉：`onFocus` 与 `onClick` 互相抵消（鼠标点击 → focus 先开、click 再取反 → 点了反而打不开）。改法：只在 `:focus-visible`（键盘焦点）时用 focus 打开。

### 3.4 cp-4（图版初始位置 + 前端优化清点）

| 项 | 实测 |
| --- | --- |
| 图版初始位置（桌面 1440×900，`scrollY=0`） | `.thinker-img` 上沿 **60px → 110px**，即**下移 50px**（图版可视高 503px ≈ 10%；容器高 780px ≈ 6.4%） |
| 图版初始位置（竖屏 780×1100） | 194px → 240px，**下移 46px** |
| 原生弹窗清点 | 全仓 `alert/confirm` **0 处**（承载页面 `RoomDetailPage.tsx` 已随 r002 redirect-06 删除；批准/拒绝入口在房内抽屉）→ roadmap 该行关闭 |
| 首页筛选条 | r004 cp-3 已修，本轮 E9 防回归（详见 review） |
