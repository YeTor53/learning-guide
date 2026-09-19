---
title: r009 台账：焦点系统重做
description: cp 切分、每步实测数字与门禁记录。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
需求见 `docs/00-requirements/r009-focus-system.md`；设计见 `design.md`。

| cp | 内容 | 状态 | 提交 | 证据 |
| --- | --- | --- | --- | --- |
| cp-r009-0 | 阶段 1 文档（需求单 + 函数级 design + ADR-0021 + 台账/审查骨架） | 进行中 | — | — |
| cp-r009-1a | 几何纯函数（均分铺满 + 加权焦点）+ 校验脚本（不动旧实现，门禁保持绿） | **完成 2026-09-19** | 见 cp-1a 提交 | E1/E2 |
| cp-r009-1b | 舞台组件切到新几何 + FLIP 动效 + 令牌 + 真机量测 | **进行中（已修两个「没铺满」真问题）** | 见 cp-1b 提交 | E0/E1/E2 |
| cp-r009-2a | 焦点权限**后端**（迁移 008 + 申请/批准/拒绝 + 用例） | **完成 2026-09-19** | 见 cp-2a 提交 | E7/E8 |
| cp-r009-2b | 焦点权限前端（房主一键取得 / 协管申请 / 退出焦点按钮互换） | planned | — | E6/E9/E10 |
| cp-r009-3 | 举手闪烁 + 格上管理动作 | planned | — | E3/E4/E5 |
| cp-r009-4 | 麦克风悬浮键 + 声波 | planned | — | E11 |
| cp-r009-5 | 收官（真机四档 + 门禁 + 文档 + review） | planned | — | E12 |

### cp-1a 实测（`node frontend/scripts/verify-stage-geometry.mjs`，区域 1160×660 = 1440×900 下的实际舞台）

| 场景 | 结果 |
| --- | --- |
| 均分 1 人 | 面积差 0.0%｜铺满率 **100.0%**｜右缘 1160/1160 |
| 均分 2 人 | 0.0%｜**98.5%** |
| 均分 3 人 | 0.5%｜**97.0%**（改前 73.2% —— 空槽重罚修好） |
| 均分 4 人 | 0.0%｜**97.6%** |
| 均分 6 人 | 0.5%｜**96.1%** |
| 均分 8 人 | 0.6%｜**94.6%**（改前 84.7%） |
| 焦点 3/4/6/8 人 | 面积份量 **1.40×**（3 人单列：高一维 1.4×；4/6/8 人：宽 1.4×）｜无重叠｜不溢出 |
| 共享 3/6 人 | mode=share，共享格 1160×507（76.8% 高），人像铺满底部条 |

**两处实现比草案改得更好的地方**（都写回 design.md）：焦点从「跨 2 格」改「加权行列」（1.40× 而非 2× 横条）；`bestGrid` 空槽惩罚 0.35 → 2.0。

### cp-1b 真机量测与两个「没铺满」真问题（2026-09-19，你在屏幕上看到后报的）

**你报的现象**：舞台上只有三条矮格子，下面一大片空白（截图 `%TEMP%\lg_r009\stage-3p.png`）。

根因两层，都已修：

| # | 根因 | 修法 |
| --- | --- | --- |
| 1 | 我给 `.live-stage-grid` 加的 `height: 100%` 把 flex 撑高覆盖成 0（父级高度 auto）→ 舞台可用区恒为 0 | 去掉 `height: 100%`（`.live-stage` 的 `flex: 1` 负责拿高度）→ 实测可用区 **1368×631** |
| 2 | 旧的 `.live-tile:not(.live-tile-focus) { flex: 0 0 168px }`（r004 缩格条定宽）+ 无高度 → **格子铺满了，格子里的画面块只有 131px 高** | 在 `.live-stage-grid` 作用域内覆盖：`.live-cell > .live-tile { width/height: 100% }`、`.live-tile-focus` 取消 aspect-ratio 限制、非焦点格不再压暗；画面填充方式做成令牌 **`--tile-fit`（默认 `cover`=铺满可能裁边；改 `contain`=完整画面留黑边）** |

修后实测（1440×900，3 人）：

| 项 | 数字 |
| --- | --- |
| 舞台可用区 | 1368 × 631 |
| 铺满率 | **98.5%**（2 人 99.3%） |
| 面积差 | 0.2%（2 人 0.0%） |
| **cell vs tile** | 450×631 vs **450×631**（完全撑满，`tileFill=true`） |
| 截图 | `stage-3p-filled.png` |

另外两条如实记录：

1. ~~动效暂未验到~~ → **已验到（同日晚补测）**：关键是 ① 无头 Chromium 默认 `prefers-reduced-motion: reduce`，必须先 `page.emulate_media(reduced_motion='no-preference')`；② 采样器要**事件驱动**（变化后再采 40 帧），固定 60/90 帧会在第三人进房前就跑完。实测（第三人进入瞬间，1440×900）：

| 帧 | 格数 | 动画数 | 动画时长 | 尺寸（逐帧收敛） |
| --- | --- | --- | --- | --- |
| t=2391ms | 2 | 0/0 | — | 679×631 \| 679×631 |
| **t=2429ms（变化瞬间）** | 3 | **1/1/1** | **240/240/220** | 679×631 \| 679×631 \| 413×581 |
| t=2455ms | 3 | 1/1/1 | 240/240/220 | 613×631 \| 612×631 \| 424×596 |
| … | … | … | … | 逐帧收敛 |
| t=2647ms | 3 | 1/1/1 | 240/240/220 | **450×631 \| 449×631 \| 449×631** |

- 时长 **240ms = `--stage-move-ms`**、**220ms = `--stage-enter-ms`**（新格进入）→ 令牌真的在生效；
- 单帧最大位移约 **66px**（679→613），远低于「格宽 60% = 270px」的防瞬移阈值 → 是连续过渡，不是一步跳到位；
- 收敛到 450/449/449 与纯函数理论值一致。

### cp-1b 追加（你的要求）：本地用户格子标识

- 你说「加个（）你标识」→ 本地用户那格右上角加一枚 **「（你）」** 胶囊（`.live-cell-self`，`pointer-events: none`，仅本地格出现），实测该类元素数 = 1；截图 `stage-self-marker.png`。
2. C 离开后 1.2 秒内仍显示 3 格：LiveKit 的断线判定本身有数秒延迟（不是布局 bug），离场格延迟摘除要在那个时点才谈得上。

### cp-2a（焦点权限后端 E7/E8）

- 迁移 `008_r009_focus_requests.sql`：`focus_requests`（pending/approved/rejected/cancelled + 待批唯一索引 `ux_focus_requests_pending`），`db_init` 应用后 `schema_migrations=8`。
- `services/focus_requests.py`：`request_focus`（协管申请，可在批→幂等；房主调用 → 400「请直接取得焦点」）、`list_focus_requests`（Host/Moderator）、`decide_focus_request`（**本人批准 → 403 `SELF_APPROVAL`**；批准同事务设焦点 + 清申请人举手）、`cancel_pending`。
- 路由：`POST/GET /api/rooms/{id}/focus-requests`、`POST /api/focus-requests/{id}/approve|reject`；错误码新增 `SELF_APPROVAL`。
- 用例 4 条（真实库、回滚事务）：协管申请 + 幂等 + **本人批准 403**；房主批准 → 焦点落到申请人且**举手被清**；拒绝 → 焦点不变；房主申请 400、参与者申请 403。
- 门禁：`pytest` **128 passed**（原 124）。
- 实现期踩到的两个真坑（都已在代码里写明原因）：① `assert_room_role` 返回的是 **MemberRow** 而不是角色字符串（`role == "host"` 永远不成立 → 房主申请被误当协管通过）；② `room_hand_raises.lowered_reason` 的 CHECK 只允许 `self/other/room_ended`，给焦点时放手的理由必须用 **`other`**（我用 `focus_granted` 直接撞约束、500）。另：新增迁移后 `test_schema` 的期望列表要跟着加（否则门禁红）。
