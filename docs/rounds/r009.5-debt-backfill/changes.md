---
title: r009.5 台账：欠账补正
description: cp 台账、用户消息台账、22 处改动的实测证据与门禁记录（cp-5 定稿）。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-20
---

<!-- overview -->
验收对照见 `review.md`；怎么改见 `design.md`。数字一律标出处：`历史`= 引自既有档案或提交；`r009.5 实测`= 本轮新跑。

## 1. cp 台账

| cp | 内容 | 状态 | 提交 | 证据 |
| --- | --- | --- | --- | --- |
| cp-r009.5-1 | 阶段 1 文档（需求单 + design + 台账/审查骨架 + 索引登记行） | 进行中 | — | E3/E11 |
| cp-r009.5-2 | 台账与 tag 补正（r009 changes 回填 + 4 tag + r008/r009 review 修正回填） | planned | — | E1~E4 |
| cp-r009.5-3 | 文档纠错与索引回填（轮次号 / 路径 / 旧文件名 / 合并顺序 / docs README §6 / roadmap §3·§7·§9） | planned | — | E5/E8 |
| cp-r009.5-4 | 配置与死代码（`.env.example` 三键 + 删 `stageLayout.ts` + 注释同步） | planned | — | E6/E7 |
| cp-r009.5-5 | 门禁与取证收官（pytest/smoke/tsc/build + E0 实测 + E11 截图 + 两页教学页 + review 定稿 + 模块页变更记录 + 索引最终回填） | planned | — | E9~E12 |

## 2. 用户消息台账（首行回执对账用）

| # | 用户原话摘要 | 回执分类 | 单号 |
| --- | --- | --- | --- |
| 1 | 「G:\VSCODE\VS_items\LearningGuide-LiveKit读取」 | 读档请求（无轮次载体性质，只读） | — |
| 2 | 「把前面的 r008 r009 检查一遍」 | 体检请求（只读，输出欠账清单） | — |
| 3 | 「用一轮.5修复，按你想的来」 | 批准（答上一问 Q1）+ 范围授权：新开 r009.5 补正轮，做法自决 | 本需求单（无 redirect 单：非对已批准设计的重定向，而是新轮次首需求） |
| 4 | （cp-5 收尾时补：确认/新意见） | — | — |

## 3. 实测证据

### 3.1 r008/r009 体检（2026-09-20，cp-0 前）

- 命令：`git rev-parse/log/status/tag`、`git grep`、`os.path` 存在性、`%TEMP%` 目录清点（脚本见本轮回复记录）。
- 结论 22 条（R1~R12 出处列）；其中「点名文件不存在」1 条：`%TEMP%\lg_r009\mic-wave.png` 实测缺失（其余 3 张在）。
- **未复现即未归因**：`cancel_pending` 0 调用点是 `git grep` 静态事实，非运行时缺陷。

### 3.2 cp-2 台账/tag（待填）

### 3.3 cp-3 纠错与索引（待填）

### 3.4 cp-4 配置与死代码（待填）

### 3.5 cp-5 门禁与取证（待填）

## 4. 门禁记录（cp-5）

| 时点 | pytest | smoke | tsc | build |
| --- | --- | --- | --- | --- |
| cp-1（进入本轮前，r009 收官口径） | 128 passed（历史） | 46/46（历史） | exit 0（历史） | 绿（历史） |
| cp-5（本轮实测） | 待填 | 待填 | 待填 | 待填 |

## 5. 文件台账

| 文件 | 动作 | 落点 cp |
| --- | --- | --- |
| `docs/00-requirements/r009.5-debt-backfill.md` | 新增 | cp-1 |
| `docs/rounds/r009.5-debt-backfill/{design,changes,review}.md` | 新增 | cp-1 |
| `docs/00-requirements/README.md` | 改（登记行 → cp-3 重排） | cp-1 / cp-3 |
| `docs/rounds/r009-focus-system/{changes,review}.md` | 改（回填与定稿） | cp-2 |
| `docs/rounds/r008-assignment-gaps/review.md` | 改（四处纠错） | cp-2 |
| `docs/00-requirements/r008-assignment-gaps.md`、`docs/rounds/r008-assignment-gaps/design.md`、`docs/00-project/ai-tools-and-models.md` | 改（轮次号/路径） | cp-3 |
| `docs/README.md`、`docs/00-project/global-roadmap.md` | 改（索引与台账回填） | cp-3 |
| `.env.example` | 改（+3 键） | cp-4 |
| `frontend/src/components/live/stageLayout.ts` | 删 | cp-4 |
| `frontend/src/components/live/stageGeometry.ts` | 改（1 行注释） | cp-4 |
| `frontend/scripts/verify-stage-motion.py` | 新增（取证脚本） | cp-5 |
| `docs/tutorials/r009.5-r008-r009-user-guide.md`、`docs/tutorials/r009.5-stage-motion-verify-dev.md` | 新增 | cp-5 |
| `docs/02-modules/r005..r009` 五页「变更记录」 | 各追加 1 行 | cp-5 |
