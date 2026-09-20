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
| cp-r009.5-1 | 阶段 1 文档（需求单 + design + 台账/审查骨架 + 索引登记行） | **完成 2026-09-20** | `59ef799` | E3/E11 |
| cp-r009.5-2 | 台账与 tag 补正（r009 changes 回填 + 4 tag + r008/r009 review 修正回填） | **完成 2026-09-20** | 见 cp-2 提交 | E1~E4 |
| cp-r009.5-3 | 文档纠错与索引回填（轮次号 / 路径 / 旧文件名 / 合并顺序 / docs README §2·§4·§5 / roadmap §3·§7·§9） | **完成 2026-09-20** | 见 cp-3 提交 | E5/E8 |
| cp-r009.5-4 | 配置与死代码（`.env.example` 三键 + 删 `stageLayout.ts` + 注释同步） | **完成 2026-09-20** | 见 cp-4 提交 | E6/E7 |
| cp-r009.5-5 | 门禁与取证收官（pytest/smoke/tsc/build + E0 实测 + E11 截图 + 两页教学页 + review 定稿 + 模块页变更记录 + 索引最终回填） | **完成 2026-09-20** | 见 cp-5 提交 | E9~E12 |

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

### 3.2 cp-2 台账与 tag（2026-09-20 实测）

- **补 tag 4 个**（附注标签，`git tag --list` 实测）：

| tag | 指向 | 提交信息 |
| --- | --- | --- |
| `cp-r009-0` | `1c4af8e` | docs(r009/cp-0): 焦点系统阶段 1 文档…… |
| `cp-r009-1b` | `e3571be` | feat(r009/cp-1b): 本地用户格子加「（你）」标识 + FLIP 动效真机验证数字 |
| `cp-r009-3a` | `0f438a2` | feat(r009/cp-3a): 举手->管理「给焦点/放下手」…… |
| `cp-r010-0` | `941046f` | docs(r010/cp-0): 阶段 1 文档…… |

  命令输出：`git tag --list 'cp-r009*'` → `cp-r009-0 cp-r009-1a cp-r009-1b cp-r009-2a cp-r009-2b cp-r009-3a cp-r009-3b cp-r009-5 cp-r009.5-1`；`git tag --list 'cp-r010*'` → `cp-r010-0`。
- `cp-r009-4` **不打**：声波无独立提交（复用 r002 的 `.live-level`，`04b6903`）；r009 `changes.md` cp-4 行已如实改写。
- **r009 `changes.md` 回填**：cp-0 行「进行中」→「完成 2026-09-19」+ 提交 `1c4af8e`；cp-1b 行「进行中」→「完成 2026-09-19」+ 提交 `2819bd7 / e3571be`；cp-4 行 →「未完成（无独立提交）」+ 原因；末尾新增「r009.5 补正」节（含 cp-3b 与复验表冲突的**裁定**：以真机复验表为准，cp-3b 那句是脚本问题）。
- **r009 `review.md` 回填**：新增 E0 行（占位，cp-5 回填实测）；E1 → 铺满率 **94.6%~100%**、面积差 **≤0.6%**「通过」；E2 → **1.40×**「通过」；E7 → 后端用例 + 前端真机「通过」；E12 → `pytest 128 / smoke 46/46 / tsc+build 绿`「通过」；overview 改为定稿说明 + 补正说明；未闭合 ③ 加 r009.5 复核结论（0 调用点、保留不删）；合并指引补前置顺序。
- **r008 `review.md` 纠错 4 处**：overview「骨架（cp-5 定稿）」→「已定稿（`b52f91f`）」；E5 补「未配密钥提示：未取证」；§5 未闭合项 2 轮次号 r009 → **r010**；§6 顺序补 r005 起点。
- **残留自检**：`docs/rounds/r008-assignment-gaps/review.md` 的 `planned`/`待测` = 0；`docs/rounds/r009-focus-system/review.md` 剩 1 处 `planned`（E0 行占位，cp-5 回填）。

### 3.3 cp-3 文档纠错与索引回填（2026-09-20 实测）

- **轮次号纠错 r009 → r010**（转写轮次，9 处 → 全部归零）：`00-requirements/r008-assignment-gaps.md` 4 处；`rounds/r008-assignment-gaps/design.md` **7 处**（原报告按「行」计 4 处，实测按出现次数为 7 处，全部替换）；`rounds/r008-assignment-gaps/review.md` 2 处；`00-project/ai-tools-and-models.md` 1 处。两轮的「变更记录」各补一行（依据写本轮）。
- **死链纠错**：`docs/rounds/r009-transcription/redirect-01.md`（不存在）→ `docs/rounds/r010-transcription/redirect-01.md`，共 3 处（r008 需求单 2 处、ai-tools 页 1 处）。`git grep -n "r009-transcription"` 实测仅剩本轮 r009.5 文档中**描述该错误**的 2 行（验收 E5 已按此口径改写）。
- **旧实现文件名纠错**：r009 需求单 cp-1 行 `stageLayout.ts` → `stageGeometry.ts`（行文案同步为实测口径「铺满 + 焦点加权 1.4× + 校验脚本」）；`rounds/r009-focus-system/motion-design.md` overview 的 `computeStageLayout` → `computeStageGeometry`（并注明取代关系）。两页各补变更记录一行。
- **索引表（`docs/00-requirements/README.md`）**：按轮次重排为 r001→…→r010→r009.5；r004 行由「待合并」改 **closed + 合并提交 `daf7696` / `round-r004-done`**；补 **r010 行**（实现中，阶段 1 文档已落）与 r009.5 行；r005~r009 行补 cp tag 实况；表下新增「合并顺序」注。
- **`docs/README.md`**：§2 指路行改指当前轮 r009.5 与下一轮 r010；§4 表按轮次重排并补 r009/r010/r009.5 三行，去掉 r004 行「待合并」尾巴；§5 backlog 追加两行登记（r006/r007 教学页缺口、`cancel_pending` 已备未接）。**§6 实测清点**的重扫**改到 cp-5**（等两页教学页落地后一次扫准，避免同轮两次扫描）——属实现细节调整（L1）。
- **`docs/00-project/global-roadmap.md`**：§3 新增 **M3 / M4 状态回填注**（M3 已完成并合 `daf7696`；M4 部分提前落地 = r008 纪要，其余未做）与 M5 实况；§7 What's next 追加第 6~11 条（r006~r010 + r009.5）并把 r004 备查段标注为已合并；§9 台账把「语音转文字」行去向由 r011 改为 **r010**、**增补三行**（r008/r009 欠账已还、`stageLayout.ts` 已删、r006/r007 教学页缺口登记）。

### 3.4 cp-4 配置与死代码（2026-09-20 实测）

- `.env.example` 追加三键（空值 + 注释）：
  `STT_BASE_URL=` / `STT_API_KEY=` / `STT_MODEL=whisper-1`（注释写明「r010 起；空 = 前端功能禁用并提示 503」）。**本机 `.env` 未改**（钥匙仍只在 owner 手里）。
- 删除 `frontend/src/components/live/stageLayout.ts`（`git rm`）；`stageGeometry.ts` 头部注释改写为「旧文件已于 r009.5 删除，历史见 git（删除前最后版本 `e3571be`）」。
- **删除后门禁复跑（E7）**：`cd frontend && npx tsc --noEmit` → **无输出（通过）**；`npm run build` → **`✓ 2006 modules transformed` / `✓ built in 3.92s` / exit 0**（仅既有 chunk >500kB 警告，r007 起既有）。
- 引用核查：`git grep -n stageLayout -- frontend/src` 实测**仅剩本轮改写后的注释**中「旧 `stageLayout.ts`」一处（描述被删对象），无 import/调用。
- 顺带：roadmap frontmatter `updated` 由 2026-09-18 更正为 **2026-09-20**。

### 3.5 cp-5 门禁与取证（2026-09-20 实测）

**门禁（本机，`learningguide` conda 环境 + 起 8000/5173）**

| 项 | 命令 | 结果 |
| --- | --- | --- |
| 后端用例 | `python -m pytest backend/tests -q`（`C:\ProgramData\miniconda3\envs\learningguide\python.exe`） | **128 passed**, 3 warnings, 41.46s（警告仍为 starlette/httpx 与 jwt 长度，与 r009 一致） |
| 真实 HTTP 冒烟 | `python backend/scripts/smoke.py --base-url http://127.0.0.1:8000` | **PASS 46/46**（含限时邀请 4 步、纪要两分支：本次 `ready` **680 字**） |
| 前端类型 | `cd frontend && npx tsc --noEmit` | **exit 0**（无输出） |
| 前端构建 | `npm run build` | **exit 0**，`✓ 2006 modules transformed` / `✓ built in 3.92s`（仅既有 chunk>500kB 警告） |

**E0 动效真机（`frontend/scripts/verify-stage-motion.py`；Playwright / conda base；1440×900；房主 + 参与者）**

| 场景 | 采样 | 位移 | 单帧最大位移 | 比值 | 动画时长 | 终点误差 | 重叠 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 入场重排 1 → 2 人 | 418 帧 / 7.0s | **344.5px** | 99.92px | **0.290** | **240ms**（= 令牌 `--stage-move-ms`）+ 220ms 淡入 | **0.0px** | 0 对 |
| 焦点切换期间重排（第三人加入） | 283 帧 / 4.8s | **25.53px** | 8.96px | **0.351** | **240ms** + 220ms | **0.0px** | 0 对 |

判据：比值 ≪ 1 即无瞬移；终点误差 = 动画末帧中心 vs 静止位置（≤1px 达标）。**E0 第 4 项**（交替说话 30 秒焦点切换 ≤3 次）需真人语音，**未取证**（脚本按纪律不发布测试音源）→ 未闭合 ④。

**E11 声波证据（同一脚本）**：`.live-level` = 容器 + **3 个 `<i>` 竖条**（单条 6px），令牌 `--mic-pulse-ms` = **320ms**；本轮 `on` 计数 **0**（未发布麦克风，符合纪律）→ 数值序列未取，截图 `%TEMP%\lg_r009.5\mic-wave.png` 已落盘。

**E12 教学流程复跑（同脚本，房主 + 两位参与者三浏览器）**：邀请面板 UI（生成码 6 位 + 倒计时「50 秒后过期 · 已用 1/5」）✓；凭码加入页预填并直接进房 ✓；举手 → 房主「给焦点」→ 举手清空、对方控制坞变「退出焦点」✓；结束房间 → 列表「讨论纪要」入口可见 → 生成纪要成功（**9.1 秒**，页面正文 858 字）✓。截图 5 张（`mic-wave / invite-panel / join-page / focus-granted / summary-page`）落 `%TEMP%\lg_r009.5\`。

**本轮新登记观测（未归因，不修）**：三人档下房主点格上「给焦点」后，**房主自己**的界面 `data-stage-mode` 仍 `uniform`、`.live-cell.is-focus` = 0（焦点未进布局），而被给焦点的一方界面正确；同脚本两人档两次运行两端同步。**同一流程复现 2/2**（两次都发生在第三人正在加入的时刻），未做最小复现 → 只登记，见 r009 `review.md` 未闭合 ⑤。

**取证脚本踩坑三条（写进开发者教学页）**：① 加了 `--use-fake-ui-for-media-stream` 会自动批准麦克风 → 真发布假麦（实测 `isMicrophoneEnabled=true`）；只给 `permissions=["camera"]` 即可避免。② `context.request` 的 origin 必须与页面一致（`127.0.0.1` 与 `localhost` 的 Cookie 不共享）→ 否则页面内请求全 401。③ 给某人开摄像头**不改变格子数**（每人在场即一格），要触发布局变化得用加入/离开/焦点切换；而**直调 HTTP 焦点接口没有广播**，本端不重排，须走 UI 点击。

## 4. 门禁记录（cp-5）

| 时点 | pytest | smoke | tsc | build |
| --- | --- | --- | --- | --- |
| cp-1（进入本轮前，r009 收官口径） | 128 passed（历史） | 46/46（历史） | exit 0（历史） | 绿（历史） |
| cp-5（本轮实测 2026-09-20） | **128 passed**（41.46s） | **PASS 46/46** | **exit 0** | **exit 0**（3.92s） |

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
| `frontend/scripts/verify-stage-motion.py` | 新增（取证脚本，324 行） | cp-5 |
| `docs/tutorials/r009.5-r008-r009-user-guide.md`、`docs/tutorials/r009.5-stage-motion-verify-dev.md` | 新增 | cp-5 |
| `docs/02-modules/r005..r009` 五页「变更记录」 | 各追加 1 行 | cp-5 |
