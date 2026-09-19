---
title: r006 重定向/确认单 01：麦克风图标不同步
description: 定性（A 实现偏差）+ 双浏览器实测证据 + 根因（图标挂在摄像头条件上）+ 拟修法与待批 Q1~Q4。
type: reference
status: proposed
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
你报：「麦克风的图标不同步」。本页给出**实测复现 + 根因**，并列出要你拍板的 4 项（Qn）。批准后按阶段 1/2 走（需求单 + design → 小步实现 → 真机取证 → review）。

## 1. 你看到的现象（原话）

> 麦克风的图标不同步

## 2. 实测复现（双浏览器，两个真实上下文同一房间，`--mute-audio`）

房间 `mic 取证 5ad1a`，A=麦主（房主）、B=听众：

| 步骤 | B 侧 A 的格子（DOM） | B 端 SDK 里 A 的麦克风（数据） | A 自己控制坞 |
| --- | --- | --- | --- |
| A **未静音** | **已经带** `MicOff` 图标（`aria-label="麦克风未开"`） | `micEnabled=true`、`micPublication.muted=false` | 「麦克风 …」（未静音态） |
| A 点「静音」后 | **仍是** `MicOff` 图标（**没有任何变化**） | `micEnabled=false`、`micPublication.muted=true` ✅ 数据同步了 | 「麦克风 \| **已静音**」 ✅ |

两个格子（焦点格 + 缩格）都恒带静音图标 —— 因为**房间里没人开摄像头**。

## 3. 根因（代码级，已核对）

`frontend/src/components/live/ParticipantTile.tsx:63`

```tsx
const showVideo = Boolean(publication && !publication.isMuted)   // ← publication 是**摄像头/共享**轨道
...
{!showVideo && <MicOff {...ICON} aria-label="麦克风未开" />}      // ← 图标挂在「没有画面」上
```

- 图标条件实际是「**有没有摄像头画面**」，**没有读麦克风状态**（全仓没有任何地方读 `participant.isMicrophoneEnabled`，只有自己的开关 `setMicrophoneEnabled`）。
- 本项目默认不开摄像头 → 所有人的格子恒定显示「麦克风未开」，看起来就是「图标不同步」。
- LiveKit 侧**数据是好的**（实测 A 静音后 B 端读到 `micEnabled=false`），所以这是**纯前端呈现缺陷**，不需要动后端、不需要新增通道。

## 4. 定性

**A（实现偏差）**：`docs/02-modules/r002-livekit-features.md` 已写死这三条 ——
- §格子（第 56 行）：「格子显示画面、姓名、角色徽标、**静音徽标**；无摄像头时显示姓名首字头像块」；
- §规则（第 61 行）：「静音/关摄像头只影响自己，不广播弹窗；**他人格子上的对应徽标实时变化**」；
- §验收点（第 62 行）：「A 关闭摄像头 → B 侧格子立即变为头像块；**A 静音 → B 侧出现静音徽标**」。

实现把「静音徽标」和「无画面头像块」混成了一个条件 → 已批准的验收点没做到。属**缺陷修正**（L1/L2，无对外面变化），不新增 ADR。

## 5. 拟修法（概要，批准后写函数级 design）

1. `ParticipantTile`：读数改用真实麦克风状态 `participant.isMicrophoneEnabled === false`（远端由 LiveKit 同步，已实测）；
2. 让格子在该状态变化时重渲染：订阅 LiveKit 的轨道静音/取消静音事件（候选：`@livekit/components-react` 的 `useIsMuted`，或 `LiveStage` 订阅 `RoomEvent.TrackMuted/TrackUnmuted` 后把状态作为 props 传下去）——**具体哪种能触发，实现时实测确认并写进 design**；
3. 徽标呈现按 Q1/Q2 定的口径改；焦点格与缩格共用同一组件，自动一起修好；
4. 验收：双浏览器（A 静音 → B 侧出现徽标；A 取消 → 消失；双向各一次）+ 截图；`pytest` / `smoke` / `tsc` / `build` 全绿。

## 6. 待批（Qn，回数字；保持建议写 `-`）

| # | 问题 | 选项 | 建议 |
| --- | --- | --- | --- |
| Q1 | **未静音**时格子要不要也显示麦克风图标？ | ① 不显示，只在静音时出现「已静音」徽标（只强调异常态，舞台更干净）② 两态都显示（开麦低调 `Mic`，静音警示 `MicOff`） | ① |
| Q2 | 静音徽标带不带文字？ | ① 带文字「已静音」（沿用既有「不做只靠图标/颜色」的口径）② 只图标 + tooltip | ① |
| Q3 | 成员抽屉（成员行）要不要也显示麦克风状态？ | ① 不加（r002/r004 的设计里抽屉只管「在不在房间」）② 加（每行一个小麦标） | ① |
| Q4 | 轮次与分支 | ① 新补轮 `r006-fix-mic-badge`，从 r005 分支拉（本页就在这个分支上）② 从 `main` 拉，等你合并 r005 之后再改 ③ 并进 r005（不推荐：r005 已收官） | ① |

## 7. 变更记录

| 日期 | 版本 | 改了什么 | 依据 |
| --- | --- | --- | --- |
| 2026-09-19 | redirect-01 | 建页：定性 + 实测证据 + 根因 + 拟修法 + Q1~Q4 | 你报「麦克风的图标不同步」 |
