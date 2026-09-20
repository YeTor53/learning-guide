---
title: r010 变更台账：语音转文字并入讨论流
description: cp 切分、每步实测数字与门禁记录、文件台账（实现期逐条追加）。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-20
---

<!-- overview -->
需求 `docs/00-requirements/r010-transcription.md`；设计 `design.md`；决定 ADR-0022；调研 `research-01/02.md`；CR 见 `cr-01.md`。
数字一律标出处：`历史` = 引自既有档案；`r010 实测` = 本轮新跑。

## 1. cp 台账

| cp | 内容 | 状态 | 提交 | 证据 |
| --- | --- | --- | --- | --- |
| cp-r010-0 | 阶段 1 文档（需求单 + 函数级设计 + ADR-0022 + 调研 01/02） | **完成 2026-09-20** | `941046f`（tag `cp-r010-0` 由 r009.5 补打） | — |
| spike-01 | 路径 A（Agents 侧转写）实测：独立环境 + 一次性脚本，主线零改动 | **完成 2026-09-20** | 见 spike 报告（未进主线提交，只提交文档） | `spike-01-path-a.md` |
| cp-r010-0b | **阶段 1 契约补齐**：design 加 §3.2 视觉契约（3 个新令牌 / 动效清单 / 界面文案 / 一次视觉验收动作）+ §5 教学契约；需求单加 §2.1 界面口径卡七项；design 状态 `approved` → **`draft`（等你读完再批）** | **完成 2026-09-20** | 见 cp-0b 提交 | 契约核对（见 §3.0） |
| cp-r010-1 | 迁移 009 + `services/stt.py`（唯一出口、可打桩）+ `repositories/transcripts.py` + 上传/列表路由 + 用例 | **完成 2026-09-20**（含 CR r010-01 依赖处置：装 `python-multipart==0.0.32`） | 见 cp-1 提交 | E1/E2/E3 |
| cp-r010-2a | 迁移 010（`external_id` 幂等键）+ `ingest_segment` + `/transcripts/segments` + `/api/stt/status` + 派单能力 + 用例（含并发幂等） | **完成 2026-09-20** | 见 cp-2a 提交 | E2/E3/E6/E14（用例 9 条，全量 **152 passed**） |
| cp-r010-2w | 转写 worker：`backend/agents/transcriber.py` + `requirements-agents.txt` + `agents.bat` + `backend/scripts/dispatch_agent.py` | **完成 2026-09-20**（离线自检通过；真机联调见 cp-5，默认用假 STT 零配额） | 见 cp-2w 提交 | 离线自检：FakeSTT 1.3s 出 3 条 |
| cp-r010-3a | **三源合一**：`build_conversation` + `GET /rooms/{id}/conversation` + 用例（聊天 / 系统事件 / 语音同一条流） | **完成 2026-09-20** | 见 cp-3a 提交 | E4（3 条用例） |
| cp-r010-3b | 前端：监听 `TranscriptionReceived` 渲染（渐进 + 定稿）+ **回传 final 段** + 转写气泡 + 进房告知条 + 控制坞「转写：开启/未开启」 | **完成 2026-09-20**（tsc exit 0 / build exit 0） | 见 cp-3b 提交 | E5/E13 |
| cp-r010-4 | 纪要接上转写素材 | planned | — | E7 |
| cp-r010-5 | 收官（真机取证、门禁、文档、review） | planned | — | E8 |

## 2. 用户消息台账（首行回执对账用）

| # | 用户原话摘要 | 回执分类 | 单号 |
| --- | --- | --- | --- |
| 1 | 「r010」 | 澄清回答（W2：点轮次名＝开工） | — |
| 2 | （cp-1 撞依赖门禁后上报） | 阻塞上报 → CR r010-01 | `cr-01.md`（超时 defaulted → 已按建议值执行） |
| 4 | 「那就测试一下A」 | 讨论决定 → 执行 spike（验证优先、不改主线） | `spike-01-path-a.md`（VALIDATED） |
| 5 | 「搜一下配额」 | 查询 → 额度/单价/场景估算落文档 | `spike-01-path-a.md` §8 |
| 6 | 「有免费档就行，只做最小程度演示，出设计方案」 | **换轨批准 + 范围收缩** → 出设计方案 | `cr-02.md`（待批）+ `design.md §9` + `ADR-0023`（proposed） |
| 3 | 「1 设计我都没看看完回复」 | 补充约束：Q1=①（补两份契约）；Q2=**设计批准延后**（你还没读） | 设计状态回 `draft`；界面口径卡 + 视觉契约 + 教学契约（cp-0b）；redirect-01 补 §9 批复台账但**保持 `proposed`** |

## 3. 实测证据

### 3.0b Spike 01：路径 A 实测（2026-09-20，独立环境，主线零改动）

**结论：路径 A 的核心未核实项已兑现** —— 多用户转写能注入房间、客户端能分辨说话人、且官方 Inference **不需要我们自备 STT key**。
关键数字（详见 `spike-01-path-a.md`）：装齐依赖 **37.6s**；worker **1 进程 / RSS 429MB**；端到端延迟 **中位 ~257ms**（假 STT，含 Cloud 日本往返）/ 官方 `transcript_delay 0.552s`（真 STT）；三端互见 `{pub1: 30, pub2: 26}`；**渐进字幕**（`final=false` → `true`）；真语音识别「今天我们先讲第一张线性回归的基本思想。」（本机离线 TTS 生成音源）。
边界：观察者（不发麦克风）不产生房间转写但其 session 会空转；**未测** 8 人、worker 掉线、长时稳定与计费。

### 3.0 cp-0b 契约补齐（2026-09-20 实测核对）

- **新增令牌真的是新增**：`--speech-bar-color` / `--speech-icon-size` / `--transcribe-notice-ms` 在 `frontend/src` 命中 **0**；
- **复用令牌真的存在**：`--panel-strong` / `--line-soft` / `--chat-body-size` / `--chat-bubble-max` / `--msg-enter` / `--t-slow` / `--ease` 均在 `global.css` 有定义；
- **动效不是新造的**：转写气泡复用 `.chat-bubble` 的 `animation: chat-enter var(--msg-enter) var(--ease)`（`global.css:1516`）与 `@keyframes chat-enter`（`global.css:1519`）；reduced-motion 降级由既有规则 `global.css:1562` 覆盖（`.chat-bubble { animation: none }`）；
- **口径卡七项全有值**（含"不适用 + 理由"项：外部参考物不适用）；
- 设计小节顺序 1~7（插入位置修正过一次：初版误把 §5 插到 §4 之前，已改正）；
- 说明：本次只落**契约文字**，样式代码一行未动（按界面类轮次规矩：视觉契约未批不动样式）。

### 3.0c cp-2a / cp-2w（2026-09-20 实测，**零外部调用**）

**cp-2a 后端（换轨后口径）**
- 迁移：`python backend/scripts/db_init.py` → `本次应用版本：010_r010_agent_transcripts`；`schema_migrations = 10`。
- 用例：`pytest backend/tests/test_transcript_segments.py -q` → **8 passed**；全量 `pytest backend/tests -q` → **152 passed**（47.01s，原 143 + 新增 9）。
- 覆盖：401/403/404；说话人必须是本房成员（400）；成功落库（`segmentIndex = NULL`、`provider = livekit`、`durationMs` 原样）；**同 `externalId` 重复上报 → `created=false` 且库里仍 1 行**；`final=false` → **204 不落库**；`durationMs=0` → 兜底为 1；文本超 2000 字 → 400；`startedAt` 非法 → 400；房间结束 → 409 且**已落转写仍可读**；`GET /api/stt/status` → `mode=agent / agentName=learning-guide-transcriber / maxSessions=5`；建房触发一次派单（spy 断言）。
- **纪律落实**：`conftest.py` 加 autouse 桩 `livekit.ensure_transcriber`（用例**零外部调用、零配额**）；需要断言的用例自行覆盖为 spy。

**cp-2w worker**
- 离线自检（`lg_agents` 环境，无网络）：`FakeSTT` 1.3 秒出 **3 条**最终稿；常量 `AGENT_NAME=learning-guide-transcriber / MAX_SESSIONS=5`。
- 组件：worker 主体 + `requirements-agents.txt`（独立环境，**不进主环境**）+ `agents.bat`（`AGENT_STT=fake|inference` 一键切换）+ `backend/scripts/dispatch_agent.py`（给已有房补派单）。
- 并发护栏：只给**有音频轨**的参与者开会话；`MAX_SESSIONS=5` 超限告警跳过。

### 3.0d cp-3a / cp-3b（2026-09-20 实测，零配额）

**cp-3a 三源合一（后端）**
- `GET /api/rooms/{id}/conversation?limit=`：把 `chat_messages(kind=chat|system)` + `transcripts` 合成**时间正序**一条流；`speech` 的 `at` 用 `started_at`，`meta` 带 `durationMs/language/externalId`；可见性沿用 `_assert_can_read`（成员含已离开 / 管理 / 房间可 ended）。
- 用例：`pytest backend/tests/test_conversation.py -q` → **3 passed**（三源排序与字段；成员/已离开/外人/未登录/limit 越界；结束后仍可读）。
- 全量：`pytest backend/tests -q` → **155 passed**（原 152 + 3）。

**cp-3b 前端（换轨后口径）**
- 新文件：`api/transcripts.ts`（status / conversation / postSegment）、`hooks/useTranscription.ts`（监听 + 渐进上屏 + 定稿落库 + agent 在场检测）、`components/live/SpeechBubble.tsx`、`components/live/TranscribeNotice.tsx`。
- 改动：`ChatPanel`（三源合并渲染，含「识别中…」渐进气泡）、`RoomSidePanel`（透传）、`RoomLivePage`（接线 + 告知条）、`DeviceBar`（只读「转写：开启/未开启」chip）、`global.css`（r010 令牌段 + 样式，含 reduced-motion）。
- 判据：`npx tsc --noEmit` **exit 0**；`npm run build` **exit 0**（2010 modules / 3.88s）；**未新增任何前端依赖**。
- 未做（如实）：跨端说话人分离、房主级转写开关、B 路径前端（不激活）。

### 3.1 cp-1（2026-09-20 实测）

- **E1 迁移**：`python backend/scripts/db_init.py`（不加 `--reset`，避免动演示数据）→ `[migrate] 本次应用版本：009_r010_transcripts`；`schema_migrations = 9`；`transcripts = 0`。
- **E2/E3 用例**：`python -m pytest backend/tests/test_transcripts_api.py -q` → **15 passed**（3.81s）。覆盖：
  - 权限：未登录 401 / 非成员 403 / 房间不存在 404 / 结束后上传 409 且**转写仍可读**（E2、边界）；
  - 未配置 STT → **503 `STT_NOT_CONFIGURED` 且不落库**（E2）；
  - STT 失败 → **502 `STT_FAILED` 且不落库**；空文本同判 502（E2）；
  - 成功 → 201 + `text/speakerId/speakerName/segmentIndex/durationMs/final/language` 齐；**打桩记录调用字节数 = 请求体长度**（音频原样透传）；
  - **幂等（E3）**：同段重传 → 仍 201、库里仍 1 行、**且不再调用 STT**（打桩调用次数 = 1）；换段号 → 2 行；两人同段号 → 互不冲突（幂等键含说话人）；
  - 校验：单段时长超上限 400、音频超体积 400、`startedAt` 非法 400、`limit` 越界 400；
  - 顺序：按 `started_at` 正序返回（后传的早时间排前）。
- **依赖门禁（CR r010-01）**：首次跑用例 13 ERROR（`RuntimeError: Form data requires "python-multipart"`）→ 停手出单 → 超时按建议值执行 → 装 `python-multipart==0.0.32` + 追加 `backend/requirements.txt` → 用例转全绿。

### 3.2 cp-2 三源合一（待填）

### 3.3 cp-3 前端采集（待填）

### 3.4 cp-4 纪要素材（待填）

### 3.5 cp-5 收官（待填）

## 3.6 分支与交接（如实记录一次操作失误与归位）

- **事实**：cp-1 的提交（`aea7326`）最初落在 **r009.5 分支**上（我沿用上一轮的工作分支，忘了 r010 有自己的分支 `req/r010-transcription`）。
- **归位（未改历史）**：
  1. `git checkout req/r010-transcription` + `git merge --ff-only aea7326` → r010 分支前移到该提交（fast-forward，与「r005 起逐轮从上一轮 HEAD 开出、随分支带下去」的既有习惯一致，因此 r010 分支同时携带 r009.5 的 7 个提交）；
  2. `git branch -f req/r009.5-debt-backfill 4c6401d` → r009.5 分支指针**移回它被 review 的定稿 tip**（`4c6401d` = `cp-r009.5-5b`），该分支内容与它自己那份 review 完全一致。
- **没有做的事**：未 `amend`、未 `rebase`、未 `reset` 任何提交；cp-1 的提交内容原样保留（仍可从 r010 分支与 `cp-r010-1` tag 取到）；r009.5 分支的定稿 tip 从未合并进任何地方，指针回退不影响已 review 的内容。
- **结论**：合并顺序仍为 `r005 → r006 → r007 → r008 → r009 → r009.5 → r010`？——**不**，仍是 **r005 → … → r009 → r010 → r009.5**（r010 分支是 r009.5 的**后代**，r009.5 分支是 r010 的祖先链上的一段）。等下：r009.5 的定稿 tip `4c6401d` 是 `aea7326` 的父提交，故 r010 分支包含 r009.5 全部内容 → 实际合并只需 **r005 → r006 → r007 → r008 → r009 → r010**（r010 分支会把 r009.5 一并带入），最后视情况再合 r009.5 分支（其 tip 已是 r010 的祖先，`git merge` 会报 "Already up to date"，等价于「r009.5 已随 r010 带入」）。
- 待收官时按上面第 6 条给出最终合并指引（在 cp-5 的 review 里定稿）。

## 4. 门禁记录

| 时点 | pytest | smoke | tsc | build |
| --- | --- | --- | --- | --- |
| cp-0（进入本轮前，r009.5 口径） | 128 passed（历史） | 46/46（历史） | exit 0（历史） | exit 0（历史） |
| cp-1（本轮实测 2026-09-20） | **143 passed**（35.01s；原 128 + 新增 15） | 未跑（cp-5 补） | 未跑（本轮无前端改动） | 未跑（同上） |

## 5. 文件台账

| 文件 | 动作 | 落点 cp |
| --- | --- | --- |
| `backend/app/db/sql/009_r010_transcripts.sql` | 新增（迁移 009） | cp-1 |
| `backend/app/config.py` | 改（`STT_*` 六项 + 启动校验） | cp-1 |
| `backend/app/db/migrate.py`、`backend/tests/test_schema.py` | 改（计数表 / 迁移清单加 `transcripts`、`009_`） | cp-1 |
| `backend/app/repositories/transcripts.py`、`backend/app/services/stt.py`、`backend/app/services/transcripts.py`、`backend/app/schemas/transcripts.py` | 新增 | cp-1 |
| `backend/app/api/routers/transcripts.py`、`backend/app/main.py` | 新增路由 / 注册 | cp-1（待 CR 批） |
| `backend/tests/test_transcripts_api.py` | 新增用例 | cp-1（待 CR 批） |
| `backend/requirements.txt` | 追加 `python-multipart==0.0.32`（CR r010-01，defaulted） | cp-1 |
| `docs/rounds/r010-transcription/{cr-01,changes}.md` | 新增 | cp-1 |
