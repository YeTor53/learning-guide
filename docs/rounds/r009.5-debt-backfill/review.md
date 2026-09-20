---
title: r009.5 审查报告：欠账补正
description: E1~E12 逐条证据、规则/文档/视觉对账、两栏清单与合并指引（cp-5 定稿，2026-09-20）。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-20
---

<!-- overview -->
**定稿**：cp-5（见 `changes.md` §1 cp 台账）。需求单 `docs/00-requirements/r009.5-debt-backfill.md`，设计 `design.md`，全部数字出处 `changes.md`（`r009.5 实测`）或既有档案（标 `历史`）。
本轮**不改产品行为**：唯一代码改动 = 删除零引用文件 `stageLayout.ts` + 一处注释；其余为文档、tag、`.env.example` 键名、取证脚本。

## 1. 验收对账

| # | 条目 | 证据 | 结论 |
| --- | --- | --- | --- |
| E1 | cp tag 补齐（`cp-r009-0/1a/1b/2a/2b/3a/3b/5` + `cp-r010-0`） | `git tag --list 'cp-r009*'` → `cp-r009-0 1a 1b 2a 2b 3a 3b 5 cp-r009.5-1..5`；`git tag --list 'cp-r010*'` → `cp-r010-0`；各指向 `design.md §2` 所列提交（附注标签） | **通过** |
| E2 | r009 台账无「进行中」残留；cp-4 写明无独立提交 | `rounds/r009-focus-system/changes.md`：cp-0 → 完成 + `1c4af8e`；cp-1b → 完成 + `2819bd7 / e3571be`；cp-4 → **未完成（无独立提交）+ 原因**（复用 r002 的 `.live-level`，`04b6903`） | **通过** |
| E3 | r009 审查无 planned 残留、E0~E12 全覆盖、含合并顺序 | `rounds/r009-focus-system/review.md`：E0~E12 逐条结论（E0 = 部分 3/4、E11 = 部分、其余通过）；「未闭合」5 条；合并指引含前置顺序 | **通过**（E0 第 4 项、E11 数值按实标未取证） |
| E4 | r008 审查四处纠错 | `rounds/r008-assignment-gaps/review.md`：overview「骨架」→「已定稿（`b52f91f`）」；E5 补「未配密钥提示子项：未取证」；§5 轮次号 → **r010**；§6 顺序补 **r005** 起点 | **通过** |
| E5 | 死链 0 命中（本轮文档引用错误路径作示例者除外） | `git grep -n "r009-transcription"` 仅剩 3 行 = r009.5 三份文档**描述该错误**的引用；`docs/rounds/r009-transcription/` 目录不存在；`grep "移至 r009"` 0 命中。**另新查出并修掉 5 处真死链**：`r006-fix-mic-badge` ×2（roadmap §9）、`tutorials/r004-room-extras.md` ×3（实际带 `-demo`）→ 全仓断链重扫 = **真死链 0** | **通过（超额）** |
| E6 | `.env.example` 含 `STT_*` 三键、无真值 | `.env.example` 新增 `STT_BASE_URL=` / `STT_API_KEY=` / `STT_MODEL=whisper-1` + 注释（r010 起用，空 = 功能禁用）；本机 `.env` **未动** | **通过** |
| E7 | `stageLayout` 0 命中 + tsc/build 绿 | `git grep -n stageLayout -- frontend/src` 仅剩 `stageGeometry.ts` 注释中「旧 `stageLayout.ts`…已删除」一句；删除后 `tsc --noEmit` **exit 0**、`npm run build` **exit 0**（`✓ 2006 modules transformed`） | **通过** |
| E8 | 索引 / docs README / roadmap 回填 | 需求索引表重排 + r004 转 `closed` + 补 r010/r009.5 行 + 合并顺序注；`docs/README.md` §2 指路、§4 表 11 行、§5 追加登记、§6 重扫（128 页 / 真死链 0）；roadmap §3 新增 M3・M4 回填注、§7 补第 6~11 条、§9 修去向列并增补 4 行 | **通过** |
| E9 | E0 动效真机量测 | 入场重排 1→2（418 帧/7.0s）：位移 344.5px、单帧最大 99.92px（比值 **0.290**）、时长 **240ms** = 令牌、**终点误差 0.0px**、重叠 0 对；焦点切换期间重排（283 帧/4.8s）：25.53px、比值 **0.351**、终点误差 0.0px。**第 4 项未取证**（需真人语音） | **部分（3/4）** |
| E10 | E11 声波证据 + 截图 | `.live-level` = 容器 + 3 个 `<i>`（6px 竖条）、令牌 `--mic-pulse-ms` = 320ms、`on` 计数 0（未发布麦克风）；`%TEMP%\\lg_r009.5\\mic-wave.png` 已落盘（其余 4 张截图同目录） | **通过（数值序列如实标未取证）** |
| E11 | 门禁四项全绿 | `pytest` **128 passed** / `smoke` **PASS 46/46**（纪要 `ready` 680 字）/ `tsc` exit 0 / `build` exit 0 | **通过** |
| E12 | 两页教学页 + 使用者页实跑 | `tutorials/r009.5-r008-r009-user-guide.md`（使用者，步骤全部实跑：邀请码 6 位 + 倒计时、凭码进房、举手→给焦点、结束→纪要 9.1 秒）与 `tutorials/r009.5-stage-motion-verify-dev.md`（开发者，含脚本用法/令牌/判据/三条踩坑）；`tutorials/README.md` 索引已加两行 | **通过** |

## 2. 规则核对（AGENTS.md + 本轮铁律）

| 规则 | 核对 | 结论 |
| --- | --- | --- |
| 未批不动代码 | 需求单 §8 有你 2026-09-20「用一轮.5修复，按你想的来」；唯一代码改动（删零引用文件）在 design §5/§8 明列为 L2 并注明授权 | **通过** |
| 一次提交一个逻辑增量 | cp-1 / cp-2 / cp-3 / cp-4（拆 4 + 4b，见下）/ cp-5 共 6 个提交，各自可独立回退 | **通过**（含一处如实说明） |
| `git add` 只写具体路径（禁 `-A`） | 每次提交均逐路径 `git add`；**cp-4 首次 `git add` 因路径含已删文件而整体失败（exit 128）**，仅提交了删除，剩余文件以 `cp-4b` 补交 —— 已记 `changes.md §3.4` | **通过（附如实记录）** |
| 历史 append-only | 无 amend / rebase / reset；tag 只新增（补号打向既有提交），未删既有 tag | **通过** |
| 密钥不入库 | 只改 `.env.example` 键名，无真值；本机 `.env` 未改 | **通过** |
| 不改历史迁移 | 本轮无迁移改动（`001~008` 未动） | **通过** |
| 文档与代码同提交 | cp-4（代码/配置）与 cp-5（脚本+教学页+审查）均含对应文档；cp-1/2/3 为纯文档提交（合法增量） | **通过** |
| 不擅自增删依赖 / 改端口 / 改目录结构 | 取证脚本用本机 conda base 已装 Playwright，**未新增仓库依赖**；脚本落在既有 `frontend/scripts/`；端口 8000/5173 未变 | **通过** |
| 轮次命名五处一致 | 需求单 `r009.5-debt-backfill` ↔ 分支 `req/r009.5-debt-backfill` ↔ cp tag `cp-r009.5-N` ↔ 轮次档案 `rounds/r009.5-debt-backfill/` ↔ 待你打 `round-r009.5-done` | **通过** |

## 3. 文档对账（两轴 + 四件套 + 覆盖矩阵）

| 项 | 结论 |
| --- | --- |
| 覆盖矩阵（需求单 §6） | **无 planned 残留**：需求单/设计/台账/审查已落地；C 使用者教学页 + D 开发者教学页 + 模块轴 5 页 + 索引轴 3 处均在 cp-5 转 landed；ADR 列明「不适用」及理由（无口径/契约变更，L2 内部结构已记 design §8） |
| 轮次轴 | `docs/rounds/r009.5-debt-backfill/{design,changes,review}.md` 齐（无 CR 单：无 L3） |
| 模块轴 | r005~r009 五页**新增「变更记录」小节**各一行（此前这 5 页无该小节，r001/r002/r004 有 → 本轮按既有先例补齐，未新立规约）；r009 实现页「遗留」第 1 条按 r009.5 证据更新 |
| 索引轴 | `00-requirements/README.md`（表重排 + r010/r009.5 行 + 合并顺序注）、`docs/README.md`（§2/§4/§5/§6）、`docs/tutorials/README.md`（两行 + 缺口段） |
| 教学页实跑 | 使用者页 5 条流程全部真机复跑（邀请面板文案、凭码落点 URL、举手→给焦点三端状态、结束→纪要 9.1 秒、`summary_ok=true`），数字均来自本轮报告 JSON |

## 4. 视觉对账（本轮不新增视觉元素，只补证据）

| 组 | 方式 | 结果 |
| --- | --- | --- |
| 声波 UI | 截图 `mic-wave.png` + DOM 断言 | 3 条 `<i>`，单条 6px，`on`=0（未发布麦克风） |
| 焦点视觉 | 截图 `focus-granted.png` + 量测 | 举手格角标「给焦点/放下手」2 个按钮；焦点格份量 1.40×（3 人档 556/396） |
| 邀请 / 加入 / 纪要 | 截图 `invite-panel.png` / `join-page.png` / `summary-page.png` | 与 r008 视觉口径一致（同一壳、等宽码、暗底卡片） |
| 零 emoji / 单一图标库 | 本轮**未新增任何图标或文案**；改动的文档与 `.env.example` 不含 emoji | **通过（无新增）** |
| 令牌未变 | `:root` 段实测 `--stage-move-ms: 240ms`、`--hand-blink-ms: 1.2s`、`--mic-pulse-ms: 320ms`、`--tile-fit: cover` | 与 r009 收官一致，未改 |

## 5. 两栏处置清单

**本轮已落地可保留**（各带出处）

1. **tag 与台账**：补 `cp-r009-0/1b/3a`、`cp-r010-0`；r009 `changes.md` 三行状态回填 + cp-3b/复验表冲突裁定（提交 = cp-2）。
2. **审查定稿**：r009（E0 补行、E1/E2/E7/E12 回填、未闭合 5 条、合并顺序）、r008（四处纠错）（提交 = cp-2）。
3. **纠错与索引**：轮次号 r009→r010 共 9 处 + 死链 3 处（另新修 5 处真死链）+ 旧文件名 2 处 + 索引/roadmap/docs README 回填（提交 = cp-3，死链 5 处在 cp-5）。
4. **配置与死代码**：`.env.example` 三键；删 `stageLayout.ts`（零引用，tsc/build 复跑绿）（提交 = cp-4 / cp-4b）。
5. **取证与教学**：`verify-stage-motion.py`（324 行，E0/E11 + 五张截图 + 报告 JSON）+ 两页教学页（提交 = cp-5）。

**未闭合 / 如实说明**

| # | 项 | 状态 | 若你判为 C 或 D 的处置 |
| --- | --- | --- | --- |
| 1 | **E11 声波数值序列** | 未取证（脚本按纪律不发布测试音源；元素/CSS 链路已证） | 顺延 r011（与 SSE 一起）；若要现在取数，需真人说话或你批准发布测试音源 |
| 2 | **E0 第 4 项**（交替说话 30 秒 ≤3 次） | 未取证（同上） | 同上，顺延 r011 |
| 3 | **r008 E5「未配密钥提示」真机** | 未取证（需临时改 `.env`） | 保持如实标注；要取证需你同意改本机 `.env` 后还原 |
| 4 | **三人档焦点同步观测**（房主端焦点未进布局） | 复现 2/2（同一流程，均含第三人正在加入），**未做最小复现、未归因** | 建议独立 fix 轮（推荐）或并入 r011；本轮不动行为 |
| 5 | **`cancel_pending` 已备未接** | 0 调用点（r009 未闭合 ③ 复核确认） | r011 接事件（焦点者离开/断线时清理待批申请） |
| 6 | **r006 / r007 教学页缺口** | 未补（本轮只补 r008/r009） | 与「测试流程全覆盖」轮一起排，或单开补正轮 |
| 7 | **r010 真机转写取证** | 等 `STT_*` 三键填值 | 你给 key 后我在 r010 补真机成功分支 |

## 6. 合并指引（由人执行）

**前置顺序**：`r005 → r006 → r007 → r008 → r009 → r010 → r009.5`（r005~r010 均未合入 `main`，逐轮从上一轮 HEAD 开出；r009.5 从 r010 HEAD 开出，故排最后）。

```bash
git checkout main
git merge --no-ff req/r009.5-debt-backfill
git tag -a round-r009.5-done -m "r009.5 完成（r008/r009 欠账补正）"
```

合并后复验（与 AGENTS.md `<check>` 一致）：
`python -m pytest backend/tests -q` → `python backend/scripts/smoke.py --base-url http://127.0.0.1:8000` → `cd frontend && npx tsc --noEmit && npm run build` → `node frontend/scripts/verify-stage-geometry.mjs`。

> 注：若你选择**先合并 r005~r010 再合并本轮**，本轮的文档改动均落在 r009.5 自己的轮次档案与既有页的补正行，冲突面很小；若顺序不同（例如先合 r009.5 再合 r010），索引与 roadmap 的同一行可能需手工择一 —— 建议按上面的顺序。
