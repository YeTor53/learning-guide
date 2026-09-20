---
title: r011 变更登记 02：焦点规则收窄——说话不再获得焦点
description: 你 2026-09-20 的口径「说话不会获得焦点！只有举手！或房主权力！」，对应的取证、定性、改动清单与生效范围。
type: reference
status: confirmed
owner: 陀梓皓
updated: 2026-09-20
---

<!-- overview -->
来源：你 2026-09-20 原话「**说话不会获得焦点！只有举手！或房主权力！**」。本单已按它实现（r011 cp-6），不再等第二次批复（你的表述是明确口径，且本轮已授权破「只修不改」纪律）。

## 1. 读back

1. **说话不再影响焦点**：谁说话都不会让舞台主区切到他（原 r009 的「说话者自动焦点」整体取消）。
2. **焦点只有两个来源**：① **举手** → 房主/协管「给焦点」（现有闭环，ADR-0021）② **房主/协管直接指定**（房主一键取得、给某人焦点）。
3. 说话仍有**视觉反馈**（成员格声波/「正在发言」），但那是**高亮**，不是焦点、不改布局。

## 2. 三比取证（改前）

| 面 | 事实 | 出处 |
| --- | --- | --- |
| 代码 | 焦点身份原为 `screenOwnerId ?? (手动焦点) ?? stableSpeaker`，说话者经 `useStableSpeaker`（去抖 800ms / 冷却 3s / 手动锁定 10s）参与焦点判定 | `frontend/src/components/live/LiveStage.tsx`（改前 :117/:136/:150）、`frontend/src/hooks/useStableSpeaker.ts` |
| 文档 | 原口径写死「优先级：共享 > 手动焦点 > **说话者** > 自己」，且 r009 澄清单 Q8 你选过「① 保留自动焦点」 | `docs/03-decisions/r004-adr-0014-focus-share-priority.md`、`docs/00-requirements/r009-focus-system.md` §口径、`docs/rounds/r009-focus-system/redirect-01.md` Q8 |
| 影响 | 舞台会在两人轮流说话时自动换主区（motion-design 里正是为它设计了防抽播参数） | `docs/rounds/r009-focus-system/motion-design.md` C4 |

## 3. 定性

**L2 行为变更**（UI 规则收窄，不动接口/数据模型/迁移）：与 ADR-0014 的第 3 档冲突 → ADR-0014 加变更记录并废止该档；与 r009 澄清单 Q8 相反 → 以你 2026-09-20 的口径为准（后口径覆盖前口径）。

## 4. 改动清单（cp-6 已落）

| 文件 | 现在 → 改成 |
| --- | --- |
| `frontend/src/components/live/LiveStage.tsx` | 焦点身份 = `screenOwnerId ?? 手动焦点 ?? null`（删掉 `stableSpeaker`）；保留 `speaking` 视觉高亮 |
| `frontend/src/hooks/useStableSpeaker.ts` | **删除**（改后零引用；历史见 git） |
| `docs/03-decisions/r004-adr-0014-focus-share-priority.md` | 决策表第 3 档标废止 + 变更记录 |
| `docs/00-requirements/r009-focus-system.md`、`rounds/r009-focus-system/motion-design.md` | 追加**指路行**（已收官轮次不回改正文，只标注新口径在哪） |
| `docs/02-modules/r009-focus-system-features.md`、`docs/02-modules/r009-focus-system.md` | 现状口径改写 + 变更记录 |
| `docs/tutorials/r009.5-r008-r009-user-guide.md` | 「规则一句话」改为：共享 > 手动焦点（含举手→给焦点） > 自己 |
| `docs/rounds/r011-debt-backfill/manual-verification.md` | 新增 **MV-11**：说话不再夺焦点、举手→给焦点仍生效 |

## 5. 生效范围与不回改的部分

- **不影响**：共享优先级（仍是最高）、焦点格放大 1.4 倍、举手闭环、协管申请焦点的权限规则（ADR-0021 全保留）。
- **不回改**：r009 轮次页里描述「当时做了什么」的句子保持原样（历史事实），只加指路行。
- **连带**：r009 E0 第 4 项（30 秒交替说话 ≤3 次）与 r011 MV-5 已无对象 —— 该项**自动作废**（说话不再改变焦点，无需演练）。
