---
title: r009.5 函数级设计：欠账补正的逐文件改动清单
description: 本轮每一处改动的「文件 → 现在是什么 → 改成什么 → 依据」，含 tag 指向表、死代码删除影响面与量测脚本设计。
type: reference
status: approved
owner: 陀梓皓
updated: 2026-09-20
---

<!-- overview -->
需求见 `docs/00-requirements/r009.5-debt-backfill.md`（R1~R12、E1~E12）。本页只写**怎么改**；每处的**证据**在 `changes.md`（本轮实测）与各轮既有档案（历史数字）。
本轮无新增接口、无迁移、无依赖变更；唯一的代码改动是删除一个零引用文件（§5）。

## 0. 导航

| 要看什么 | 去哪 |
| --- | --- |
| 为什么改（欠账清单） | 需求单 §1（22 处出处列） |
| tag 打在哪 | 本页 §2 |
| 每个文档改哪几行 | 本页 §3 |
| 代码与配置改什么 | 本页 §4/§5 |
| 取证脚本怎么设计 | 本页 §6 |
| 教学页写什么 | 本页 §7 |
| 回退怎么做 | 本页 §9 |

## 1. 数据层

无迁移。本轮不改 schema、不改数据、不删数据。

## 2. git 层：cp tag 补打（R1）

| tag | 指向提交 | 依据（提交信息自称 / 台账行） | 备注 |
| --- | --- | --- | --- |
| `cp-r009-0` | `1c4af8e` | `docs(r009/cp-0): 焦点系统阶段 1 文档——需求单 + 函数级设计 + ADR-0021` | 新增 |
| `cp-r009-1b` | `e3571be` | `feat(r009/cp-1b): 本地用户格子加「（你）」标识 + FLIP 动效真机验证数字`（cp-1b 的最后一个提交，前一个为 `2819bd7`） | 新增 |
| `cp-r009-3a` | `0f438a2` | `feat(r009/cp-3a): 举手->管理「给焦点/放下手」（后端 grant_focus_from_hand + 格上角标）` | 新增 |
| `cp-r010-0` | `941046f` | `docs(r010/cp-0): 阶段 1 文档——需求单 + 函数级设计 + ADR-0022` | 新增 |
| `cp-r009-4` | **不打** | cp-4（声波）**无独立提交**：`changes.md` cp-4 行提交栏为空；房内声波复用 r002 已落地的 `.live-level`（引入提交 `04b6903`），本轮只接线 | 台账如实写明 |

打 tag 用 `git tag -a <名> -m "<说明>" <sha>`（附注标签，与既有 cp tag 一致）。**不动**既有 `cp-r009-1a/2a/2b/3b/5`；**不删**任何 tag；**不改**历史。

## 3. 文档改动清单（逐文件：改成什么）

### 3.1 `docs/rounds/r009-focus-system/changes.md`（R2/R4）

| 位置 | 现在 | 改成 |
| --- | --- | --- |
| §1 cp 表 cp-r009-0 行 | 状态 `进行中`，提交 `—` | 状态 `**完成 2026-09-19**`，提交 `1c4af8e` |
| §1 cp 表 cp-r009-1b 行 | 状态 `**进行中（已修两个「没铺满」真问题）**` | 状态 `**完成 2026-09-19**（两个「没铺满」真问题已修）`，提交 `2819bd7 / e3571be` |
| §1 cp 表 cp-r009-4 行 | 状态 `**部分**（元素在、数字待补）`，提交 `—` | 状态 `**未完成（无独立提交）**`，提交 `—`，证据栏写：「声波复用 r002 已落地的 `.live-level`（`04b6903`），本轮只接线；数值序列未取 → 顺延 r011（见 review 未闭合清单 ①）」 |
| 文件末尾 | 止于「焦点闭环真机复验」表 | 追加「## r009.5 补正（2026-09-20）」一节：① 补 tag 清单（上表）② **裁定 cp-3b 与复验表的冲突**：cp-3b 段「『放下手』路径本轮未验到」是当时**脚本**问题（脚本用 API 清焦点、无广播），同文件末尾复验表 #2 已真机验到（举手格 1 → 0）→ **以复验表为准**，原句保留并加括号注明 ③ 指向本需求单 |

### 3.2 `docs/rounds/r009-focus-system/review.md`（R3）

| 位置 | 现在 | 改成 |
| --- | --- | --- |
| 概述 | 「cp-5 定稿时补齐。」 | 「定稿：`a0bcecf`（cp-5）；数字来源见 `changes.md` 对应节；**r009.5 补正**：补 E0 行、回填 E1/E2/E7/E12、补合并顺序与未闭合项 ③（`2026-09-20`）」 |
| E0 | **缺行** | 新增行：动效（终点误差 ≤1px / `--stage-move-ms` / 无瞬移 / 交替说话 30 秒 ≤3 次）→ 结论按本轮 cp-5 实测（r009.5 新测，标明「r009.5 实测」） |
| E1/E2 | `待测` / `planned` | `通过`：铺满率 **94.6%~100%**（1/2/3/4/6/8 人六档）、面积相对差 **≤0.6%**、焦点格份量 **1.40×**；出处 `changes.md §cp-1a 实测` + `node frontend/scripts/verify-stage-geometry.mjs` |
| E7 | `**后端通过**（前端按钮待 cp-2b）` | `**通过**`：后端 4 条用例 + 前端真机（协管文案即时变「已申请焦点」、房主端待批行 = 1）；出处 `changes.md §cp-3b 真机复验表 #3` |
| E12 | `待测` / `planned` | `通过`：`pytest` **128 passed** / `smoke` **PASS 46/46** / `tsc`+`build` 绿；出处 `changes.md §收官门禁（cp-5）`；**r009.5 复跑数字**另有记录 |
| 「未闭合」清单 ③ | 「只有后端 `cancel_pending` 函数、未接事件」 | 补「**r009.5 复核（2026-09-20）**：`git grep cancel_pending` 仍 0 调用点 → 确认；**保留不删**，待 r011 接事件（焦点者离开/断线时清理其待批申请）」 |
| §合并指引 | 仅 `merge --no-ff req/r009-focus-system` | 补前置：**先按序合 r005 → r006 → r007 → r008 → r009**，再 r010，最后 r009.5（本分支从 r010 HEAD 开出） |

### 3.3 `docs/rounds/r008-assignment-gaps/review.md`（R5）

| 位置 | 现在 | 改成 |
| --- | --- | --- |
| 概述 | 「状态：**骨架**（cp-5 定稿）。」 | 「状态：**已定稿**（cp-5 = 「收官…」提交）。r009.5 补正（2026-09-20）：E5 补「未取证」标注、§5 轮次号改 r010、§6 补前置顺序。」 |
| E5 行 | 「前端纪要页与入口 … **通过**」 | 结论后补：「**未配密钥提示子项：未取证**——`changes.md §3.2` 自述当时已填 `LLM_API_KEY` 未复现（探针 2.5 秒 vs 真实耗时 4.6~6.8 秒），本项一并如实标注，不因代码写了就当已过」 |
| §5 未闭合项 2 | 「已整体移到 **r009**」 | 「已整体移到 **r010**（`docs/rounds/r010-transcription/`，决定 `ADR-0022`）」 |
| §6 合并指引 | `# 建议顺序：r006 → r007 → r008` | `# 建议顺序：r005 → r006 → r007 → r008；其后 r009 → r010 → r009.5` |

### 3.4 `docs/00-requirements/r008-assignment-gaps.md`（R6）

| 位置 | 改成 |
| --- | --- |
| §2 第三条（语音转文字整体移至 r009） | 轮次号改 **r010**，路径改 `docs/rounds/r010-transcription/redirect-01.md`，并加「（原定 r009，2026-09-19 焦点系统插入后顺延为 r010）」 |
| §5 cp 切分 cp-4 行 | 同上（轮次号 + 路径） |

### 3.5 `docs/rounds/r008-assignment-gaps/design.md`（R6）

§1.2「迁移 `008_*_transcripts.sql`（**移至 r009**）」、§2.2 `app/schemas/transcripts.py`、§2.6 `app/services/transcripts.py` 三处标题，与 §6 变更记录中相关表述：轮次号一律改 **r010**（保留「移至」语义）。

### 3.6 `docs/00-project/ai-tools-and-models.md`（R6）

| 位置 | 现在 | 改成 |
| --- | --- | --- |
| §2 表「语音转文字」行 | `（r009，规划）` + 路径 `docs/rounds/r009-transcription/redirect-01.md` | `（r010，规划）` + `docs/rounds/r010-transcription/redirect-01.md`；备注补「方案已定：云端 Whisper 兼容（ADR-0022）；三键已进 `.env.example`，待填值」 |
| §1 工具表 | 「（请补：如 Claude Code / Codex / Cursor 等）」 | **保持不动**（交付物需你本人确认，本轮不代填）；在本页加一行注明「本页 status: draft，待 owner 确认后随交付提交」 |

### 3.7 `docs/00-requirements/README.md`（R10）

| 位置 | 改成 |
| --- | --- |
| 表行 r004 | 状态改 `closed（2026-09-19；已合并 `daf7696` 并打 `round-r004-done`）`，完成 tag 列同步 |
| 表内顺序 | 按轮次重排：r001→r002→r003→r004→r005→r006→r007→r008→r009→r010→r009.5 |
| 缺行 | 补 r010（`**实现中**：阶段 1 文档已落（需求单 + 设计 + ADR-0022 + 两份调研），cp-1 起未开工`）与 r009.5（本页需求单，状态 `approved`） |
| r005~r009 行 | 状态列「实现完成…待合并」保留，完成 tag 列补「（合并顺序 r005→…→r010→r009.5，见 `r010 redirect-01 §6` 与 r009.5 需求单）」 |

### 3.8 `docs/README.md`（R10）

| 位置 | 现在 | 改成 |
| --- | --- | --- |
| §2 表「本轮（r004）要做什么」 | 指 r004 | 指 **r009.5**（本页需求单）与 r010（下一轮实现） |
| §4 轮次档案表 | 缺 r009/r010 行；r004 行尾巴仍写「待合并打 round-r004-done」 | 补 r009（含 r009.5 补正说明）/r010/r009.5 行；去掉 r004 行尾巴 |
| §6 实测清点 | 「脚本扫描 `docs/` 下 61 个 .md」+ 旧状态分布 | 用 **r009.5 重扫结果**替换（页数 / 状态分布 / 断链 0 命中），标注扫描日期与脚本口径 |
| §5 backlog 表 | 4 行 | 追加两行登记：① r006/r007 使用者/开发者教学页缺口（本轮只补 r008/r009，见需求单 §2）② `cancel_pending` 已备未接（r011） |

### 3.9 模块页「变更记录」（R10）

`docs/02-modules/r005-fix-capacity.md`、`r006-ui-sync-polish.md`、`r007-topic-and-scrollhint.md`、`r008-assignment-gaps.md`、`r009-focus-system.md` 各追加一行：

> 2026-09-20 · r009.5 补正：<该轮> 的台账/审查回填、轮次号纠错、索引回填（无行为变更）；详见 `docs/rounds/r009.5-debt-backfill/`。

### 3.10 `docs/00-project/global-roadmap.md`（R10）

| 位置 | 现在 | 改成 |
| --- | --- | --- |
| §3 里程碑 | 只有 M1/M2 有状态回填注 | 加 **M3 状态回填注**：r004 完成并合并（`daf7696`）；M3 后续增量 = r005~r009（补轮，均未合并）；M4 部分提前落地（r008 纪要） |
| §7 What's next | 只写到 r005「当前」 | 补 r006/r007/r008/r009/r010 条目（各一行：内容 + 状态 + tag）与 **r009.5（本轮）**；写明合并顺序 |
| §9 台账 | 「语音转文字…去向列写 r011」；「好友 + 在线用户」行末尾截断 | 修 r010；补全截断行；新增三行：① r008/r009 台账与 tag 欠账（本轮已还）② `stageLayout.ts` 死代码（本轮已删）③ r006/r007 教学页缺口（登记，未还） |

## 4. 配置面（R8）

`frontend/` 与 `backend/` 代码都不读 `STT_*`（r010 的 `config.py` 才读）。本轮只补 `.env.example` 占位：

```ini
# —— 语音转文字（r010 起；OpenAI 兼容 Whisper /audio/transcriptions；空 = 功能禁用） ——
STT_BASE_URL=
STT_API_KEY=
STT_MODEL=whisper-1
```

依据：需求单 §2「只改 `.env.example`」；r008 需求单 §3-E12 与本需求单 R8。**不填真值**；本机 `.env` 不动。

## 5. 代码改动：删零引用文件（R9，L2）

- 删除 `frontend/src/components/live/stageLayout.ts`（导出 `computeStageLayout`；ADR-0021 已由 `stageGeometry.ts` 的 `computeStageGeometry` 取代）。
- 引用核查（实测）：`git grep -n stageLayout -- frontend/src` 唯一命中是 `stageGeometry.ts:4` 的**注释**；该注释一并改写为「本模块取代 r004 的 `stageLayout`（已于 r009.5 删除，历史见 git）」。
- 影响面：`LiveStage.tsx` 已 import `computeStageGeometry`，不受影响；`frontend/scripts/verify-stage-geometry.mjs` 用的是新函数，不受影响。
- 删除后必须复跑 `tsc --noEmit` + `npm run build`（验收 E7）。
- **保留不删**：`app/services/focus_requests.py::cancel_pending` 与 `app/repositories/focus_requests.py::cancel_pending_for_user`（0 调用点但为 r011 既定用途；在 r009 实现页「未闭合」处标明「已备未接」）。

## 6. 取证脚本设计（R11）

新增 `frontend/scripts/verify-stage-motion.py`（Playwright，Python；用本机 conda base 已装的 Playwright，**不新增仓库依赖**；与既有 `verify-stage-geometry.mjs` 同目录、同职责）。

| 函数 | 职责 | 输出的判据 |
| --- | --- | --- |
| `login(ctx, email)` | 用演示账号登录，返回 cookie 上下文 | — |
| `join_room(ctx, room_id)` | 进房并等待舞台就绪（等待 `.live-cell` 出现） | 参与者数 |
| `measure_cells(page)` | 读每个格子的 `getBoundingClientRect` | 面积、坐标、铺满率（与 `verify-stage-geometry.mjs` 同口径，互相印证） |
| `measure_transition(page, trigger)` | 触发一次布局变化，采 `element.getAnimations()` 的 `duration` 与首末帧 `transform` | 过渡时长 = `--stage-move-ms`；终点误差 = 末帧矩阵与目标 rect 之差 ≤ 1px；采样序列里无「跳变」（单帧位移 > 整段位移 60% 即判瞬移） |
| `shot(page, name)` | 截图落 `%TEMP%\lg_r009.5\<name>` | 文件存在 |

纪律（沿用既有）：无头运行；**加 `--mute-audio`**；**不发布假麦克风**；不抢前台、不按进程名杀进程；起服务用分离进程（无 `--reload`）。

## 7. 教学页（R12）

| 页 | 受众 | 内容要点（实跑为准） |
| --- | --- | --- |
| `docs/tutorials/r009.5-r008-r009-user-guide.md` | 使用者 | ① 讨论纪要：结束房间 → 卡片「讨论纪要」→ 生成 → 重新生成；未配密钥时的表现 ② 限时邀请：抽屉「邀请」tab → 30/60 秒 + 次数 → 复制链接 → 对方 `/join?code=` 直接进 ③ 焦点系统：举手 → 管理「给焦点」/「放下手」、房主「取得焦点」、协管「申请焦点 → 他人批准」、焦点者「退出焦点」 ④ 声波与状态条读法 |
| `docs/tutorials/r009.5-stage-motion-verify-dev.md` | 开发者 | 怎么跑两个校验脚本（几何 / 动效）、参数令牌在哪改（`--stage-*` / `--hand-blink-*` / `--mic-pulse-*` / `--tile-fit`）、判据与本次实测数字 |

## 8. 本轮设计变更记录

| 级别 | 变更 | 依据 | 用户批复 |
| --- | --- | --- | --- |
| L2 | 删 `stageLayout.ts`（模块内部结构/文件拆分变化，接口与行为不变） | 全仓 0 引用 + ADR-0021 取代 | 你 2026-09-20「按你想的来」 |
| L1 | `.env.example` 增 3 键、文档纠错、tag 补打 | 契约面不变（键名为既有口径：r008 §4 / r010 §3） | 同上 |

无 L3。CR 单不适用（变化不触及对外可见面、数据、验收标准、依赖、范围）。

## 9. 回退方案

| 改动 | 回退 |
| --- | --- |
| 文档/配置提交（cp-1/2/3/4/5） | `git revert <sha>`（append-only，禁 reset） |
| 补打的 4 个 tag | `git tag -d cp-r009-0 cp-r009-1b cp-r009-3a cp-r010-0` |
| 删除的 `stageLayout.ts` | `git checkout e3571be -- frontend/src/components/live/stageLayout.ts`（删除前最后版本） |
| 整轮放弃 | 分支 `req/r009.5-debt-backfill` 未合并 → 留分支不合并即可（与主干无关） |
