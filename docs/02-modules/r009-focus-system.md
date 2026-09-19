---
title: r009 实现页：焦点系统重做（均分铺满 + 举手—焦点闭环 + 声波）
description: 均分铺满几何、FLIP 动效、焦点权限三分流、举手给焦点闭环的决定性事实源与实测数字。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
需求见 `docs/00-requirements/r009-focus-system.md`；几何/权限设计 `design.md`；动效设计 `motion-design.md`；决定 ADR-0021。

## 1. 布局：均分铺满（`components/live/stageGeometry.ts`）

| 面 | 要点 |
| --- | --- |
| 纯函数 | `bestGrid`（空槽**重罚 2.0**，否则 3 人会选 2×2 留洞）/ `distribute` / `distributeWeighted` / `computeStageGeometry`（`empty|uniform|focus|share` 四模式） |
| 焦点份量 | **加权行列** `FOCUS_WEIGHT=1.4`（草案里的「跨 2 格」实测是 2:1 横条、面积 2×，已废） |
| 舞台组件 | `LiveStage` 绝对定位格子 + `data-flip-id` 稳定节点；`stageRef` 必须用 **callback ref**（`useRef` 在「空态→网格」切换时 effect 不重跑、尺寸恒 0） |
| 铺满率 | 1/2/3/4/6/8 人 = **100% / 99.3% / 98.5% / 97.6% / 96.1% / 94.6%**，面积差 ≤0.6% |
| 内层撑满 | 旧 `.live-tile:not(.live-tile-focus){flex:0 0 168px}`（r004 缩格条）必须在新布局作用域覆盖，否则「格子铺满但画面块只有 131px」 |

## 2. 动效：FLIP（`hooks/useFlipTransition.ts`）

- 唯一动画入口；时长/缓动全部读 CSS 令牌（`--stage-move-ms` 等）；`prefers-reduced-motion` 归零。
- 实测（第三人进入）：三格动画数 1/1/1、时长 **240/240/220ms**，尺寸 679→613→…→450 逐帧收敛，单帧最大位移 66px（阈值 270px）。
- 无头浏览器验收两坑：Chromium **默认 `reduced-motion: reduce`**（须 `emulate_media`）；采样器要**事件驱动**（固定帧数会跑在变化之前）。

## 3. 焦点权限（ADR-0021 D2）

| 角色 | 举手键 | 行为 |
| --- | --- | --- |
| 房主 | **取得焦点** | `POST /rooms/{id}/focus`（直接生效） |
| 协管 | **申请焦点** | `POST /rooms/{id}/focus-requests` → 另一位管理身份批准 |
| 参与者 | **举手** | 管理在举手格上「给焦点 / 放下手」 |
| 任何人（正持焦点） | **退出焦点** | 替换举手键 |

- 后端：`focus_requests`（迁移 008，四态 + 待批唯一索引）、`request_focus` / `decide_focus_request`（**本人批准 403 `SELF_APPROVAL`**，批准同事务设焦点 + 清举手）/ `grant_focus_from_hand`（原子版）。
- 同步纪律：**广播走既有路径**（`focus.setFocus` / `hands.lowerOther` 带 DataChannel），新接口只做原子兜底；批准后由批准人补一次广播。
- 举手闪烁：`.live-cell.is-hand` + `hand-breathe` 动画（`--hand-blink-ms` 1.2s），纯视觉、不参与几何。

## 4. 验证数字（2026-09-19）

| 项 | 结果 |
| --- | --- |
| 门禁 | `pytest` **128 passed**｜`smoke` **PASS 46/46**｜`tsc`/`build` exit 0 |
| 三人真机 | 举手→给焦点：房主端焦点格 1 / 举手格 0，参与者端焦点格 1 且按钮变「退出焦点」；放下手：举手格 1→0；协管申请→文案「已申请焦点」→ 房主批准 → **三端焦点格均为 1**、协管文案「退出焦点」→ 协管点退出 → 焦点格 0 |
| 截图 | `%TEMP%\lg_r009\{stage-3p-filled,grant-focus,focus-approved,mic-wave}.png` |

## 5. 遗留（如实）

1. **声波（E11）只做到「控件与 `.live-level` 元素存在」**：我按 `.live-level` 的宽度取样恒为 13px（那是容器宽度），没取到随声音变化的那个量（可能是内层 fill 的宽度或 CSS 变量），**数字待补**。
2. 焦点回退：焦点者离开房间时的自动清理已由 r004 逻辑承担，本轮未新增用例。
3. SSE 实时通道归 r011（本轮待批申请用 8 秒轮询）。
