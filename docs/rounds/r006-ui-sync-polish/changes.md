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
| cp-r006-3 | 个人信息浮窗 + 哲学语句池 | planned | — | E6/E7 |
| cp-r006-4 | 图版初始位置下移 + 前端优化清点处置 | planned | — | E8/E9 |
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
