---
title: docs 导览（现状清点与指路）
description: 本仓 docs/ 的目录地图、每类页的用途、当前真相页指路、索引与台账清单，以及实测出的漂移/待办。本页只描述现状与指路，不引入任何新规约。
type: reference
status: active
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
这是 `docs/` 的入口页：**先看哪一页、哪个是当前真相、哪几处已知不一致**。全部内容为 2026-09-19 的**实测清点**（脚本扫描 `docs/` 下 61 个 .md）。
本页**不定义规约**：文档命名与落位口径由 owner 的规范统一给出；本页与规范冲突时以规范为准。

## 1. 目录地图（类别 → 放什么 → 有几页）

| 目录 | 放什么 | 页数 | 索引 |
| --- | --- | --- | --- |
| `00-project/` | 方向：目标、里程碑、项目级台账 | 1 | `global-roadmap.md` 自身含 §3 里程碑、§7 轮次台账、§9 遗留台账 |
| `00-requirements/` | 每轮**需求单**（契约：目的/边界/验收） | 5 | `00-requirements/README.md`（轮次索引表） |
| `01-architecture/` | 总设计与**每轮增量**设计 | 3 | 无独立索引，见本文 §3 |
| `02-modules/` | 模块页：实现页（代码事实）+ 功能页（人可见行为） | 6 | **`02-modules/README.md`**（模块 → 轮次页 → 当前真相页） |
| `03-decisions/` | ADR：`global-` 跨轮 / `rNNN-` 轮内 | 15 | 无独立索引，见本文 §3 |
| `04-style/` | 视觉与文案风格 | 1 | `global-style.md` |
| `rounds/` | 每轮档案：`design.md`（设计）/`changes.md`（变更台账）/`review.md`（审查报告）+ `redirect-NN.md`（过程中的重定向单） | 21（4 轮） | 见本文 §4 |
| `tutorials/` | 教学页（使用者与开发者） | 6 | **`tutorials/README.md`**（受众索引） |
| `99-archive/` | backlog 构思页（提前产出、目标里程碑未到） | 4 | 见本文 §5 |
| 根 | `glossary.md`（术语表） | 1 | — |

## 2. 现在要看哪一页（按目的指路）

| 你的目的 | 打开 |
| --- | --- |
| 现在做到哪、下一步是什么 | `00-project/global-roadmap.md` §3、§7；`00-requirements/README.md` |
| 本轮（r004）要做什么、怎么算做完 | `00-requirements/r004-room-extras.md` |
| 本轮怎么实现（函数级） | `rounds/r004-room-extras/design.md`（§0 有导航） |
| 房间/实时模块的当前实现事实 | `02-modules/r002-livekit.md`（实现）+ `r002-livekit-features.md`（功能）；**M3 能力（群聊/举手/焦点/共享）见 `02-modules/r004-room-extras.md`（实现）+ `r004-room-extras-features.md`（功能）；人数上限与房间事件见 `r005-fix-capacity{,-features}.md`；界面同步与优化见 `r006-ui-sync-polish{,-features}.md`** |
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
| r006-ui-sync-polish | `r006-ui-sync-polish.md`（实现完成，待合并） | ✅ | ✅ | ✅（定稿） | — | 分支 `req/r006-ui-sync-polish`，cp tag `cp-r006-0..4` |
| r005-fix-capacity | `r005-fix-capacity.md`（实现完成，待合并） | ✅ | ✅ | ✅（定稿） | — | 分支 `req/r005-fix-capacity`，cp tag `cp-r005-0..4` |
| r004-room-extras | `r004-room-extras.md`（实现完成，**已合并** `daf7696` / `round-r004-done`） | ✅ | ✅ | ✅（定稿） | — | 分支 `req/r004-room-extras`，cp tag `cp-r004-1..7`；待合并打 `round-r004-done` |

## 5. backlog（`99-archive/`）

| 页 | 目标 | 状态 |
| --- | --- | --- |
| `r001-ahead-m4-summaries.md` + `-features.md` | M4 LLM 纪要 | backlog |
| `r002-ahead-invites.md` | 邀请能力（未定里程碑） | backlog |
| `r003-ahead-m4-ended-rooms-archive.md` | M4 归档页（含 A1~A9 已拍板口径） | backlog |
| `r005-ahead-test-process.md` | r005 测试流程（全覆盖）：七层模型 / 用例编号 / 证据等级 / `verify.bat` 管线 / 8 条待拍板 | backlog |

## 6. 实测清点（2026-09-19，61 个 .md）

**状态字段分布**：`closed` 5 · `accepted` 12 · `draft` 14 · `proposed` 4 · `backlog` 4 · `active` 1 · redirect 单的 `confirmed-A/B/C` 6 · `superseded` 1 · 无 front matter 1。

**已知不一致（按影响排序；r001/r002 已合并打 tag，改动需新轮次或 owner 批准）**

| # | 现象 | 位置 | 处置 |
| --- | --- | --- | --- |
| 1 | 该页**没有 front matter**（其余 60 页都有） | `rounds/r002-livekit/design.md` | **待批**：r002 已合并，补 FM 属回改；已在 r004 `changes.md` 与 roadmap §9 登记 |
| 2 | `status` 字段被写成一整句话 | `rounds/r002-livekit/redirect-06.md`（`confirmed-delete（用户 2026-09-18：「删了吧」）`） | **待批**：同上 |
| 3 | 页 `status` 仍是 `draft`，但所属轮次已收官 | `01-architecture/r002-realtime-architecture.md`、`02-modules/r002-livekit.md`、`-features.md`、`rounds/r002-livekit/changes.md` | **待批**：同上（r003/r004 的 `draft` 属正常在途） |
| 4 | 模块事实源分散：同一模块跨多轮多页 | 房间/实时：`r001-rooms.md`、`r001-rooms-features.md`、`r002-livekit.md`、`r002-livekit-features.md`（r004 后将 +2 页） | 已用 `02-modules/README.md` 给「当前真相页」指路；**是否合并为单页属规约变更，等 owner 规范** |
| 5 | 曾被怀疑「DDL 事实源页停更」——**实测为否**（2026-09-19） | `backend/tests/test_schema.py` 以 `02-modules/r001-rooms.md` §3 为 DDL 事实源 | 实测 `pytest backend/tests/test_schema.py -k "design_page or counted_tables or ordered"` → **3 passed**，即该页仍与 `001_schema.sql` 逐字一致；`003_r002_host_uniqueness.sql` 记在 r002 两页与 r002 架构增量页（各 6/6/3 次命中）。仅该页 `updated` 日期偏旧，**无内容漂移，不回改** |
| 6 | ~~规划中的页尚未创建~~ **已闭合**：`03-decisions/r004-adr-0015-home-first-screen.md`、`02-modules/r004-room-extras{,-features}.md`、`tutorials/r004-room-extras-demo.md` 均已在 cp-3/cp-6/cp-7 落地（使用者教学页实际文件名为 `-demo.md`） | — | 已落地 |
| 7 | 页面里大量「`docs/xxx/yyy*.md`」通配/花括号简写（非点击链接） | 多页表格与正文 | 仅记录：不是断链，但不可点击；新页书写时按需写全路径 |

**扫描口径**：页数 = `docs/**/*.md`；状态 = front matter 的 `status`；断链 = 相对 `](*.md)` 与反引号 `docs/*.md` 路径的存在性检查（详见本轮 `changes.md`）。
