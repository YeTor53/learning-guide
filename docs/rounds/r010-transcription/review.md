---
title: r010 审查报告：语音转文字并入讨论流（换轨后）
description: E1~E14 逐条证据、规则/文档/视觉对账、两栏清单与合并指引（cp-5 定稿，2026-09-20）。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-20
---

<!-- overview -->
**定稿**：cp-5（见 `changes.md` §1 cp 台账）。需求单 `docs/00-requirements/r010-transcription.md`；设计 `design.md`（§9 为换轨后口径）；决定 ADR-0023；换轨单 `cr-02.md`；实测 `spike-01-path-a.md`。
**验证纪律（你 2026-09-20 定）**：不再花配额做实验——本轮全部验证走**桩 + 离线假 STT**，真机 E2E 也是假 STT。

## 1. 验收对账

| # | 条目 | 证据（数字出处） | 结论 |
| --- | --- | --- | --- |
| E1 | 迁移 009/010 落库 | `db_init.py` → `本次应用版本：010_r010_agent_transcripts`，`schema_migrations = 10`；房间实测 35 行：`external_id` **全非空**、`segment_index` **全空**、`provider = livekit`、`model = learning-guide-transcriber` | **通过** |
| E2 | 三条分支：worker 在场 → 上屏 + 落库；不在场 → 提示不报错；`STT_MODE=off` → 提示且不上报 | 在场：三人 E2E（气泡 32/33/35、库 35 行、三端 `转写：开启`）；不在场：截图轮实测（worker 崩后）chip 显示「未开启」、`errors: []`；**`STT_MODE=off` 分支未验**（改 `.env` 即可，未做） | **部分（off 分支未验）** |
| E3 | 幂等：同 `externalId` 多端冗余上报只落一行 | 用例 4 条；E2E 实测 **56 次 POST → 唯一 35 行**（三端冗余上报未重复） | **通过** |
| E4 | 三源合一（聊天 + 系统事件 + 语音）时间正序 | 用例 3 条；E2E `/conversation` `kinds = [speech, system]`、界面同列（截图 `shot-discussion.png` 里「同学S 加入了房间」与转写气泡同流） | **通过** |
| E5 | 前端不再采集/上传音频（`STT_MODE=agent`） | 代码事实：`useTranscription` 只监听 `TranscriptionReceived` 并 POST **文本**；全仓无 MediaRecorder 分段上传逻辑 | **通过** |
| E6 | `.env.example` 新增 `STT_MODE / STT_AGENT_NAME / STT_MAX_SESSIONS` | `.env.example` 尾部（`STT_MODE=agent` 默认） | **通过** |
| E7 | 转写进纪要素材（R5） | cp-4：用例用桩捕获给 LLM 的 messages，断言「线性回归的关键是最小二乘」与「语音转写」段都在素材里，`inputDigest` 含 `speech=1`；全量 156 passed | **通过** |
| E8 | 索引 / docs README / roadmap / 教学页索引回填 | 本提交（需求索引行、`docs/README.md` §4、roadmap §7/§9、`tutorials/README.md`） | **通过** |
| E9 | （r009.5 遗留：E0 动效第 4 项 / E11 声波数值） | 与 r010 无关，仍在 r009 review 未闭合清单 | 不适用 |
| E10 | （r009.5 遗留：三人档焦点观测） | 同上 | 不适用 |
| E11 | 门禁四项 | `pytest backend/tests -q` → **156 passed**；`smoke.py` → **PASS 46/46**；`npx tsc --noEmit` → exit 0；`npm run build` → exit 0（2010 modules / 3.83s） | **通过** |
| E12 | 教学页 + 教学契约 | `docs/tutorials/r010-transcription-user-guide.md`（含演示前置、探活、免费档限制、常见疑问）；`design.md` §5 教学契约 | **通过** |
| E13 | 3 人真机：渐进上屏 / 落库 / 三端一致 / 归属正确 | E2E：三端 chip 全「开启」、气泡 32/33/35、`speakers = [房主F, 乙F, 丙F]`、`agent_seen_after_seconds = 13.4`、`errors: []`；截图 `shot-discussion.png` / `shot-notice.png`。**渐进「识别中…」在前两轮截图里可见，但每 2 秒的自动采样为空**——假 STT 的文本一次性给出，`synchronizer` 几乎瞬时定稿；真 STT 的渐进已由 spike 实测（`一章` → `第一章线性回归等` → `…的基本思想`） | **通过（渐进采样如实标未捕到）** |
| E14 | worker 不在场时：显示未开启、无未捕获异常、无 5xx | 截图轮实测（worker 已崩）：chip「未开启」、页面无 alert、`errors: []`、后端日志无 5xx | **通过** |

## 2. 规则核对（AGENTS.md + 本轮纪律）

| 规则 | 核对 | 结论 |
| --- | --- | --- |
| 未批不动代码 | 阶段 1 批（`cr-01/02`）+ ADR-0023；换轨前先出 spike 与 CR | **通过** |
| 一次提交一个逻辑增量 | cp-2a（后端）/ cp-2w（worker）/ cp-3a（三源合一）/ cp-3b（前端）/ cp-4（纪要接线）/ cp-5（收官），各自可独立回退 | **通过** |
| `git add` 只写具体路径 | 每次逐路径 `git add`；无 `-A` | **通过** |
| 历史 append-only | 无 amend / rebase / reset 提交；cp-5 修复以新提交追加 | **通过** |
| 密钥不入库 | `.env` 未动；worker 凭据只经进程环境；测试全桩（`conftest` 自动桩 `ensure_transcriber`） | **通过** |
| **不打真实外部服务（省配额）** | 全部用例零外部调用；worker 用 `AGENT_STT=fake` 跑 E2E；真 STT 只在 spike 期用过一次（已记录） | **通过** |
| 不擅自增删依赖 | 后端仅加 `python-multipart`（CR-01）；worker 依赖独立清单 `requirements-agents.txt`（不进主环境）；前端**零新增** | **通过** |
| 不改端口 / 目录结构 | 8000 / 5173 不变；worker 放 `backend/agents/`（新子目录，README 有说明） | **通过** |

## 3. 文档对账（两轴 + 覆盖矩阵）

| 项 | 结论 |
| --- | --- |
| 覆盖矩阵（需求单 §6） | 全部转 `landed`（需求单 / design / ADR / 两 CR / spike / changes / review / 模块页 / 教学页 / README / 索引） |
| 轮次轴 | `docs/rounds/r010-transcription/{design,changes,review,cr-01,cr-02,spike-01-path-a}.md` 齐 |
| 模块轴 | 实现页/功能页：**本轮未新建**（转写行为已在 design §9 + 教学页写清）；按 r009 先例可在下一轮补，已登记未闭合 ⑥ |
| 索引轴 | 需求索引 r010 行、`docs/README.md` §4、roadmap §7/§9、`tutorials/README.md` 均已回填 |

## 4. 视觉对账（五组证据）

| 项 | 做法 | 实测 | 结论 |
| --- | --- | --- | --- |
| 令牌扫描 | 新增令牌只 3 个且都在 `global.css` 的 r010 段 | `--speech-bar-color` / `--speech-icon-size` / `--transcribe-notice-ms`（后两者被引用） | 通过 |
| 零 emoji / 单一图标库 | `lucide-react` 的 `Mic` / `Info`；界面无 emoji | grep 无新图标库 | 通过 |
| 截图 | 1440×900：`shot-notice.png`（告知条）、`shot-discussion.png`（讨论流） | 2 张，`%TEMP%\lg_r010_e2e\` | 通过 |
| 真机复看（两轮） | 第一轮发现**转写 agent 占了一个舞台格子**（`agent-AJ_swWMGfsZzzUF`）→ 修（`isAgentParticipant` + 舞台/在线身份过滤）→ 第二轮复看：舞台只剩 2 个真人格子 | 已修，见未闭合 ⑤ | **通过（含一次真机发现并修复）** |
| 降级复测（reduced-motion） | 转写气泡与告知条均在 CSS 里受 `prefers-reduced-motion` 约束 | 规则已写；未做开关复测 | 部分（未复测） |

## 5. 两栏处置清单

**本轮已落地可保留**
1. 后端：迁移 010（`external_id` 幂等键）、`ingest_segment`、`/transcripts/segments`、`/conversation`、`/stt/status`、建房派单、`dispatch_agent.py`（提交 cp-2a/cp-3a）。
2. worker：`backend/agents/transcriber.py` + `requirements-agents.txt` + `agents.bat`（含自动重启）+ 离线假 STT 档（提交 cp-2w、cp-5）。
3. 前端：`useTranscription`（监听/渐进/回传）、`SpeechBubble`、`TranscribeNotice`、`DeviceBar` 状态 chip、`ChatPanel` 三源合并、agent 过滤（提交 cp-3b、cp-5）。
4. 纪要接线：转写进素材 + `speech=` 计数（提交 cp-4）。
5. 文档：需求单 v7、design §9 与 §3.2、ADR-0023、CR-01/02、spike-01（含配额）、changes、本 review、教学页。

**未闭合 / 如实说明**

| # | 项 | 状态 | 处置建议 |
| --- | --- | --- | --- |
| ① | **worker 会因 LiveKit FFI 一次性 panic 退出**（实测 1 次：`FFI Panic: invalid request: timed out waiting for ReadyForRoomEventRequest after ConnectCallback`，日志 `%TEMP%\lg_r010_e2e\worker.log`） | 根因在 livekit 侧，未深查；**已加自动重启**（`agents.bat`）+ 控制坞如实显示「未开启」 | 演示前确认进程窗口在跑；若要更稳，下一轮加看门狗/健康上报 |
| ② | `STT_MODE=off` 分支未验 | 未取证 | 下一轮补一条用例或真机 |
| ③ | 渐进字幕在假 STT 下未采到样本 | 真 STT 下已由 spike 证实 | 真 STT 对齐时补采样 |
| ④ | `duration_ms` 在假 STT 下恒为 1（真 STT 应由 segment 提供） | 兜底逻辑已写（0 → 1），界面在 ≤1s 时不显示时长 | 真 STT 对齐时复核 |
| ⑤ | 真机发现并修复：转写 agent 曾占用舞台格子 | **已修**（`isAgentParticipant` + 两处过滤，tsc/build 绿 + 复看截图） | 无需再动 |
| ⑥ | 模块轴实现页/功能页未建 | **已补（2026-09-20）**：`docs/02-modules/r010-transcription.md`（实现页，含 §7 扩展点）+ `r010-transcription-features.md`（功能页 F-44~F-47）；模块索引与 `docs/README` 指针已回填 | 闭合 |
| ⑦ | 房主级「全房关转写」、跨端说话人分离、B 路径前端 | 范围外 | 记入 roadmap §9 |
| ⑧ | 免费档额度/并发（3 人演示内安全） | 已查证写入 `spike-01-path-a.md` §8 | 演示 ≤3 人 |
| ⑨ | `/api/stt/status` 仍返回 `segmentSeconds = 8`（B 路径的「8 秒分段」残留字段）——A 路径下分段由官方 synchronizer 决定，字段易误读 | 前端**未使用**该字段（只读 `mode`），无界面误导 | 改契约（重命名/移除）属 L3 → **登记待批**，不擅自改 |
| ⑩ | `docs/rounds/r002-livekit/redirect-03.md` 有 1 处假死链（正文里的竖线被当成链接目标，形如 `](alert｜confirm｜prompt)`） | 非本轮引入（r002 遗留） | 登记，随下一轮文档维护一并修 |

## 5b. 复核补正（2026-09-20，cp-5b）

你要求「检查一遍」后的只读复验结果，**结论未变**，补正了四处文档与实现对不上的地方：

| # | 发现 | 处置 |
| --- | --- | --- |
| 1 | 需求单 §4 的 **E2/E3/E5/E6 仍是 B 路径口径**（"上传音频 → 201"、"关闭后不再上传"），与换轨后实现不符——需求单是验收基准，留着会让 E 编号与验收内容对不上 | 已按换轨口径改写，并逐条标注「2026-09-20 补正」 |
| 2 | 需求单 §4 只到 **E8**，而本 review 用了 E1~E14 | 已在需求单 §4 增补 **E9~E14**（E9/E10 为 r009.5 占位、本轮不适用），编号与本文对齐 |
| 3 | 需求单 §5 的 cp 切分表还是换轨前的旧计划（`cp-2`/`cp-3`、含 `ConversationPanel`） | 已按实际切分重排，并注明「以 `changes.md` §1 台账为准」 |
| 4 | `design.md` §9.8 的 cp 名残留旧写法（`cp-3`） | 已改为 `cp-2a/2w/3a/3b/4/5` 并对齐验收点 |

**复验本身**：门禁四项在最终树复跑全绿（pytest **156 passed** / smoke **46/46** / tsc exit 0 / build exit 0，2010 modules 3.92s）；`/openapi.json` 端点 **32** 个，转写相关 4 个；`/api/stt/status` → `{mode: agent, agentName: learning-guide-transcriber, maxSessions: 5, segmentSeconds: 8}`；密钥扫描 0 处；工作区干净；断链扫描 135 页 → 真死链 1 处（**r002 历史文件**里的 `](alert|confirm|prompt)` 假链接，非本轮引入，见未闭合 ⑨）。

## 6. 合并指引（由人执行）

**顺序**：`r005 → r006 → r007 → r008 → r009 → r010`（本分支 `req/r010-transcription` 已包含 r009.5 的全部提交，故无需单独合 r009.5）。

```bash
git checkout main
git merge --no-ff req/r010-transcription
git tag -a round-r010-done -m "r010 完成（语音转文字并入讨论流，换轨 Agents 侧）"
```

合并后复验：`pytest backend/tests -q` → `python backend/scripts/smoke.py --base-url http://127.0.0.1:8000` → `cd frontend && npx tsc --noEmit && npm run build`。
演示（第三个进程）：`agents.bat`（或 `set AGENT_STT=fake && agents.bat` 零配额联调）→ `dev.bat` → 建房进房，等控制坞显示「转写：开启」（实测约 13 秒）。
