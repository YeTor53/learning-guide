---
title: docs 导览（现状清点与指路）
description: 本仓 docs/ 的目录地图、每类页的用途、当前真相页指路、索引与台账清单，以及实测出的漂移/待办。本页只描述现状与指路，不引入任何新规约。
type: reference
status: active
owner: 陀梓皓
updated: 2026-09-20
---

<!-- overview -->
这是 `docs/` 的入口页：**先看哪一页、哪个是当前真相、哪几处已知不一致**。目录地图与指路为 **2026-09-20 的实测清点**（脚本扫描 `docs/` 下 **128** 个 .md；§6 为本次重扫结果）。
本页**不定义规约**：文档命名与落位口径由 owner 的规范统一给出；本页与规范冲突时以规范为准。

## 1. 目录地图（类别 → 放什么 → 有几页）

| 目录 | 放什么 | 页数 | 索引 |
| --- | --- | --- | --- |
| `00-project/` | 方向：目标、里程碑、项目级台账 | 3 | `global-roadmap.md` 自身含 §3 里程碑、§7 轮次台账、§9 遗留台账 |
| `00-requirements/` | 每轮**需求单**（契约：目的/边界/验收） | 12 | `00-requirements/README.md`（轮次索引表） |
| `01-architecture/` | 总设计与**每轮增量**设计 | 3 | 无独立索引，见本文 §3 |
| `02-modules/` | 模块页：实现页（代码事实）+ 功能页（人可见行为） | 19 | **`02-modules/README.md`**（模块 → 轮次页 → 当前真相页） |
| `03-decisions/` | ADR：`global-` 跨轮 / `rNNN-` 轮内 | 23 | 无独立索引，见本文 §3 |
| `04-style/` | 视觉与文案风格 | 1 | `global-style.md` |
| `rounds/` | 每轮档案：`design.md`（设计）/`changes.md`（变更台账）/`review.md`（审查报告）+ `redirect-NN.md`（过程中的重定向单） | 51（11 轮） | 见本文 §4 |
| `tutorials/` | 教学页（使用者与开发者） | 9 | **`tutorials/README.md`**（受众索引） |
| `99-archive/` | backlog 构思页（提前产出、目标里程碑未到） | 5 | 见本文 §5 |
| 根 | `glossary.md`（术语表） | 1 | — |

## 2. 现在要看哪一页（按目的指路）

| 你的目的 | 打开 |
| --- | --- |
| 现在做到哪、下一步是什么 | `00-project/global-roadmap.md` §3、§7；`00-requirements/README.md` |
| **当前轮（r010 转写）**要做什么、怎么算做完 | `00-requirements/r010-transcription.md` §4（E1~E14）；实现完成，**待合并** |
| 当前轮怎么实现（逐文件改动清单） | `rounds/r010-transcription/design.md` §9（换轨后口径）；模块事实源 `02-modules/r010-transcription.md` |
| 说话怎么变成文字、演示前起什么 | `tutorials/r010-transcription-user-guide.md` |
| 房间/实时模块的当前实现事实 | `02-modules/r002-livekit.md`（实现）+ `r002-livekit-features.md`（功能）；**M3 能力（群聊/举手/焦点/共享）见 `02-modules/r004-room-extras.md`（实现）+ `r004-room-extras-features.md`（功能）；**语音转写见 `02-modules/r010-transcription.md`（实现）+ `r010-transcription-features.md`（功能）；人数上限与房间事件见 `r005-fix-capacity{,-features}.md`；界面同步与优化见 `r006-ui-sync-polish{,-features}.md`；主题与首屏引导见 `r007-topic-and-scrollhint{,-features}.md`** |
| 账号/首页模块 | `02-modules/r001-accounts.md` + `r001-accounts-features.md` |
| 为什么这么决定 | `03-decisions/` 下对应 ADR（跨轮的以 `global-` 开头） |
| 怎么跑起来 / 怎么演示 | `tutorials/r002-livekit-setup.md`、`tutorials/r002-livekit-demo.md`；房内四件事（群聊/举手/焦点/共享）见 `tutorials/r004-room-extras-demo.md` |
| 动手改代码前先读什么 | `tutorials/r002-livekit-dev-guide.md` |
| 术语（房间码、等候室、一次性讨论…） | `glossary.md` |

## 3. 架构页与 ADR 一览（按轮次）

- 总设计：`01-architecture/r001-app-architecture.md`（r001 起，仍是当前总设计）
- 增量：`r002-realtime-architecture.md`（M2 实时层）、`r004-realtime-extras-architecture.md`（M3 实时层：HTTP 真相源 + Data Channel 加速）
- ADR：`global-adr-0001-selfhosted-livekit.md`（跨轮）；`global-adr-0002-docs-convention.md`（跨轮，**proposed，未拍板**）；`r001-adr-0002..0010`（9 个）；`r002-adr-0011..0012`（2 个）；`r004-adr-0013..0015`（3 个）；`r005-adr-0016`（容量口径）、`r006-adr-0017`（界面口径）

## 4. 轮次档案现状

| 轮次 | 需求单 | design | changes | review | redirect | 状态 |
| --- | --- | --- | --- | --- | --- | --- |
| r001-skeleton | `r001-skeleton-accounts-rooms.md`（closed） | ✅ | ✅ | ✅ | — | 已合并 `round-r001-done` |
| r002-livekit | `r002-livekit-room.md`（closed） | ✅（**该页无 front matter**，见 §6） | ✅ | ✅（2026-09-19 定稿） | redirect-01~07 | 已合并 `round-r002-done` |
| r003-end-room-entry | `r003-end-room-entry.md`（closed，2026-09-19 回填） | ✅ | ✅ | ✅ | redirect-01~02 | 已合并 `round-r003-done`（`694caeb`） |
| r004-room-extras | `r004-room-extras.md`（closed，2026-09-19 回填） | ✅ | ✅ | ✅（定稿） | — | **已合并** `daf7696` / `round-r004-done`；cp tag `cp-r004-1..7` |
| r005-fix-capacity | `r005-fix-capacity.md`（实现完成，待合并） | ✅ | ✅ | ✅（定稿） | — | 分支 `req/r005-fix-capacity`，cp tag `cp-r005-0..4` + `4b` |
| r006-ui-sync-polish | `r006-ui-sync-polish.md`（实现完成，待合并） | ✅ | ✅ | ✅（定稿） | redirect-01~02 | 分支 `req/r006-ui-sync-polish`，cp tag `cp-r006-0..5` |
| r007-topic-and-scrollhint | `r007-topic-and-scrollhint.md`（实现完成，待合并） | ✅ | ✅ | ✅（定稿） | redirect-01 | 分支 `req/r007-topic-and-scrollhint`，cp tag `cp-r007-0..8` |
| r008-assignment-gaps | `r008-assignment-gaps.md`（实现完成，待合并） | ✅ | ✅ | ✅（定稿；r009.5 纠错 4 处） | — | 分支 `req/r008-assignment-gaps`，cp tag `cp-r008-0..4` |
| r009-focus-system | `r009-focus-system.md`（实现完成，待合并） | ✅ | ✅（r009.5 回填） | ✅（定稿；r009.5 补 E0 并回填 E1/E2/E7/E12） | redirect-01 | 分支 `req/r009-focus-system`，cp tag `0/1a/1b/2a/2b/3a/3b/5`（4 无独立提交） |
| r010-transcription | `r010-transcription.md`（实现完成，待合并；覆盖矩阵全 `landed`） | ✅（§9 换轨后口径） | ✅（cp-1~cp-5 + cp-5b 补正） | ✅（定稿；含 §5b 复核补正） | redirect-01 + research-01/02 + cr-01/02 + spike-01 | 分支 `req/r010-transcription` @ `b32656f`；换轨口径＝Agents 侧识别（ADR-0023）；cp tag `cp-r010-0/0b/0c/1/1b/2a/2w/3a/3b/4/5/5b`；worker 走独立环境 `lg_agents` |
| r009.5-debt-backfill | `r009.5-debt-backfill.md`（实现完成，待合并） | ✅ | ✅ | ✅（定稿） | — | 分支 `req/r009.5-debt-backfill`，cp tag `cp-r009.5-1..5`；本轮**不改产品行为** |

## 5. backlog（`99-archive/`）

| 页 | 目标 | 状态 |
| --- | --- | --- |
| `r001-ahead-m4-summaries.md` + `-features.md` | M4 LLM 纪要 | backlog |
| `r002-ahead-invites.md` | 邀请能力（未定里程碑） | backlog |
| `r003-ahead-m4-ended-rooms-archive.md` | M4 归档页（含 A1~A9 已拍板口径） | backlog |
| `r005-ahead-test-process.md` | r005 测试流程（全覆盖）：七层模型 / 用例编号 / 证据等级 / `verify.bat` 管线 / 8 条待拍板 | backlog |
| （无页）r006/r007 教学页缺口 | r006 界面同步、r007 主题与首屏两轮的**使用者/开发者教学页**均未建（r009.5 只补 r008/r009 两轮，见 `00-requirements/r009.5-debt-backfill.md` §2） | 登记待排期（无页可指，r009.5 不新建 backlog 页：属文档欠账非功能构思） |
| （无页）`cancel_pending` 已备未接 | 焦点者离开/断线时清理其待批申请：后端函数已存在但 0 调用点（r009 review 未闭合 ③） | 登记待排期（r011 接事件；r009.5 保留函数不删） |

## 6. 实测清点（2026-09-20 重扫，128 个 .md）

> 扫描口径：页数 = `docs/**/*.md`；状态 = front matter 的 `status`；断链 = 相对 `](*.md)`（滤通配符）与反引号 `docs/*.md` 路径的存在性检查。本次重扫由 r009.5 执行（上一条快照为 2026-09-19 的 61 个 .md，口径未含 `rounds/` 全量与新增轮次）。

**状态字段分布**：`draft` 51 · `accepted` 17 · `proposed` 16 · `approved` 15 · `closed` 11 · `backlog` 5 · `active` 3 · `confirmed-A/B/C` 6 · `superseded-G1` 1 · `status` 写成整句 1 · 无 `status` 字段 2。
（`draft` 偏多属正常：r005~r010 与 r009.5 均**未合并**，未收官轮次的页保持 `draft`。）

**目录分布**：`rounds/` 51 · `03-decisions/` 23 · `02-modules/` 19 · `00-requirements/` 12 · `tutorials/` 9 · `99-archive/` 5 · `00-project/` 3 · `01-architecture/` 3 · 根 2 · `04-style/` 1。

**断链检查**：真死链 **0** 处。本轮（r009.5）修掉 4 处真死链——`docs/rounds/r006-fix-mic-badge/redirect-01.md` ×2（roadmap §9，目录名实为 `r006-ui-sync-polish`）、`docs/tutorials/r004-room-extras.md` ×3（实际文件名带 `-demo`）。剩余 4 处命中均为**非死链**：① r009.5 文档里 3 处**引用错误路径作为待修示例**（本轮 E5 口径已排除）② `ADR-0022` 里的通配简写 `research-01/02.md`。

### r010 收官快照（2026-09-20，137 个 .md）

> 口径同上（`docs/**/*.md`）。相比上一条 128 页快照：+2 模块页（`02-modules/r010-transcription{,-features}.md`）、+7 轮次页（`rounds/r010-transcription/`：design/changes/review/cr-01/cr-02/spike-01/research 补充）。

**目录分布**（合计 137）：`rounds/` **56** · `03-decisions/` 24（+ADR-0023） · `02-modules/` 21 · `00-requirements/` 12 · `tutorials/` 10（+r010 使用者页） · `99-archive/` 5 · `00-project/` 3 · `01-architecture/` 3 · 根 2 · `04-style/` 1。

**断链检查**：真死链 **1** 处——`rounds/r002-livekit/redirect-03.md` 里的 `](alert｜confirm｜prompt)`（正文竖线被当成链接目标，r002 遗留，非 r010 引入，见 r010 review 未闭合 ⑩）；其余 136 页 0 死链。

**已知不一致（2026-09-20 复核；上一条清单里的 1/3/6 已闭合）**

| # | 现象 | 位置 | 处置 |
| --- | --- | --- | --- |
| 1 | ~~该页没有 front matter~~ **已闭合** | `rounds/r002-livekit/design.md` | 页内 `updated` 注明「2026-09-19 补 front matter」，实测有 FM 且 `status: closed`，正文未改 |
| 2 | `status` 字段被写成一整句话 | `rounds/r002-livekit/redirect-06.md`（`confirmed-delete（用户 2026-09-18：「删了吧」）`） | **仍待批**：r002 已合并，属回改；已在 roadmap §9 登记 |
| 3 | ~~页 `status` 仍是 `draft`，所属轮次已收官~~ **已闭合** | `01-architecture/r002-realtime-architecture.md`、`02-modules/r002-livekit{,-features}.md`、`rounds/r002-livekit/changes.md` | 实测四页均为 `status: closed`（2026-09-19 元数据修正） |
| 4 | 模块事实源分散：同一模块跨多轮多页 | 房间/实时：`r001-rooms.md`…`r009-focus-system.md` 共 12 页 | 已用 `02-modules/README.md` 给「当前真相页」指路；是否并页属规约变更，等 owner 规范 |
| 5 | DDL 事实源页 `updated` 偏旧（实测无内容漂移） | `02-modules/r001-rooms.md`（`backend/tests/test_schema.py` 以它为准） | 不回改，见 r004 `changes.md` |
| 6 | ~~规划中的页尚未创建~~ **已闭合** | r004 的三页 | 已在 cp-3/cp-6/cp-7 落地 |
| 7 | 教学页缺口：r006 / r007 两轮无使用者 / 开发者页 | `docs/tutorials/`（最新覆盖 r005；r008/r009 由 r009.5 补） | **登记待排期**（`docs/tutorials/README.md` 末段、roadmap §9）；属文档欠账非功能构思，不新建 backlog 页 |
| 8 | 三人档焦点同步观测（r009.5 新登记，未归因） | 见 `docs/rounds/r009-focus-system/review.md` 未闭合 ⑤ | **登记**：建议独立 fix 轮或并入 r011 |
| 9 | 页面里大量「`docs/xxx/yyy*.md`」通配/花括号简写（非点击链接） | 多页表格与正文 | 仅记录；真死链已在上表清 0，通配写法的可点击性属书写习惯，等 owner 口径 |
