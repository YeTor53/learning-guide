---
title: r010 需求单：语音转文字并入讨论流
description: 默认开启、说的话并入文字对话、与成员进出等管理信息同源；含 STT 获取方案（调研结论已并入）。
type: reference
status: approved
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
澄清单 `docs/rounds/r010-transcription/redirect-01.md`；调研 `research-01.md` / `research-02.md`；设计 `design.md`；决定 **ADR-0022**。你 2026-09-19 口头答复「1」= 先补调研再出设计（本页即其产物）。

## 1. 需求（R）

| # | 需求 | 说明 |
| --- | --- | --- |
| R1 | **默认开启** | 一进房间即转写（**2026-09-20 换轨后**：由房间侧转写 worker 承担，见 design §9）；**关掉自己的麦克风即不参与转写**（原「一键关本端上传」在 A 路径下不成立，已按 ADR-0023 D5 改写） |
| R2 | **说的话并入「文字对话」** | 转写文本进入房间讨论流（与群聊同一条流），不是单独的「转写片段」列表 |
| R3 | **与成员进出等管理信息同流** | 系统消息（加入/离开/被移出/移交/房间结束/满员未通过）与转写、聊天三源合一，构成完整会议记录 |
| R4 | **STT 获取方案** | 先讲清用哪家、怎么拿、成本限额、云/自建、离线兜底（见 §3） |
| R5 | 转写进纪要 | r008 已预留「转写文本（有则带）」，本轮接上 |
| R6 | 隐私 | 进房一次性明确告知 + **关麦即不转写** + **不保留原始音频**（只存文本）。**换轨后必须如实改写措辞**：音频会经 LiveKit Cloud 与识别服务商（原「音频只到我方后端」已不成立，见 ADR-0023 D4） |

## 2. 口径与边界

- 转写对象 = **本端麦克风**（路径 B）；说话人恒为本人（无跨端归属问题）。
- **只落最终稿**；同一段话的中间稿不落库（`final` 字段保留以对齐官方契约）。
- 分段 **8 秒**（`STT_SEGMENT_SECONDS`），静音段不上传（能量门限）；单段上限 30 秒 / 10MB（超出 400）。
- 未配 STT → 前端开关禁用并提示；接口 503 `STT_NOT_CONFIGURED`（沿用 r008 错误码）。
- 房间结束后不可再上传（409 `ROOM_ENDED`），但转写文本随房间**只读可查**。
- 可见范围：本房间全员（会议记录公开）；不做「谁关掉谁看不见别人的」。
- 音频不落盘（内存 → STT → 丢弃），日志不打印文本内容。

## 2.1 界面口径（r010，七项必答）

> 本轮**有用户可见界面**（进房告知条、控制坞「转写」开关、「讨论」流里的转写气泡），故按界面类轮次补齐口径卡；视觉契约（令牌表 / 动效清单 / 文案）落在 `design.md` §3.2。

- **用户群与目标**：正在开线上讨论的学生与老师；目标是「没人打字，会后也有完整文字记录」。做完能看到：自己那句话变成一条带说话人、带时长的气泡，出现在抽屉「讨论」里，并进入纪要素材。
- **风格基调**：**沿用项目既有暗色编辑风**（ink 分层底色 + 单强调色 + 细网格/噪点质感层）；一句话定义：**转写不是新界面，而是既有「讨论」流里的一个新气泡类型**——同一气泡壳、同一令牌语言、靠左侧色条与麦克风小图标区分。
- **参考物（写明看哪一层）**：

  | 来源 | URL | 看哪一层 |
  | --- | --- | --- |
  | 仓库内既有实现 `frontend/src/components/live/ChatPanel.tsx` | （本仓） | 气泡排版与层级、间距、时间戳位置 |
  | 仓库内既有令牌 `frontend/src/styles/global.css` `:root` 段 | （本仓） | 取色与尺寸取值口径（禁自拟数值） |
  | 外部参考 | **不适用** | 本轮无新风格层，不引外部视觉参考（避免与既有语言打架） |

- **技术栈**：React 18 + Vite + TypeScript（既有）；样式只用 `global.css` 的 CSS 变量；图标用既有 **Lucide**（单一图标库）。
- **界面细节（换轨后）**：控制坞只读状态 chip（「转写：开启/未开启」）；告知条按钮为「关掉我的麦克风」/「知道了」；转写气泡靠左侧色条区分。
- **动效范围**：**要** ①转写气泡入场（**复用**既有 `@keyframes chat-enter`：透明度 0→1 + 上移 6px、`--msg-enter` 120ms，不新增 keyframes）②进房告知条 30 秒后自动收起（`--transcribe-notice-ms`）。**不要** 新 keyframes、页面切换转场、气泡逐字打字机、气泡入场错峰级联、声波竖条节奏改造（声波在 r009 已定，本轮不动）。
- **令牌与图标**：沿用 `global.css` `:root`；本轮**只新增 3 个**：`--speech-bar-color`(rgba(124, 240, 196, 0.45))、`--speech-icon-size`(14px)、`--transcribe-notice-ms`(30000，无单位、JS 读)；气泡壳 / 字号 / 最大宽 / 入场动画全部**复用** r004 既有令牌；图标库 Lucide（`Mic` / `Info` / `X` 三个既有图标，不新增图标库）。
- **硬条款**：单一图标库 **开**、零 emoji **开**、界面文案禁内部词 **开**（轮次 / 里程碑 / 检查点 / cp-NNN / 作业 / 考核 一律不出现在界面）—— **本轮是否改：否**（三条全沿用，无豁免）。

## 3. STT 获取方案（调研后的定稿）

| 方案 | 怎么拿 | 结论 |
| --- | --- | --- |
| **A. 云端 Whisper 兼容 REST**（硅基流动 / 百炼 / 火山 / OpenAI） | 申请 key → `POST {STT_BASE_URL}/audio/transcriptions`（multipart） | **本轮采用**（`.env` 已有 `STT_*` 三键预留） |
| B. 本地 faster-whisper | 服务端跑模型 | **离线兜底**：`STT_BASE_URL` 指向本机自建服务即可，代码不变 |
| C. LiveKit Agents 侧转写 | `livekit-agents` worker + STT 插件 | **不本轮做**，见 ADR-0022 的迁移点（官方文档：Agent 做 STT 时转写会实时发布到前端，AgentSession 默认开启） |
| D. 浏览器 Web Speech | 前端直连 | 不用（中文质量与可复现性不足） |

成本口径（估算，按 A）：Whisper 兼容服务普遍按音频分钟计费；8 秒一段 → 1 小时会议约 450 段、总音频 60 分钟 → 单场成本在「分/角」量级；本项目为演示规模，量级无压力。**限额**：单段 30 秒 / 10MB，前端 8 秒切段即天然限流。

## 4. 验收条目（E）

| # | 条目 | 证据 |
| --- | --- | --- |
| E1 | 迁移 `009_r010_transcripts` 落库（表 + 段唯一索引） | `db_init` 输出 |
| E2（换轨后按 design §9.7 修订） | `POST /rooms/{id}/transcripts` 上传音频 → 201 返回文本；未配 STT → 503；超限 → 400；结束后 → 409 | 用例（打桩 STT） |
| E3 | 幂等：同 `segmentIndex` 重传 → 不产生重复行 | 用例 |
| E4 | `GET /rooms/{id}/conversation` 三源合一：聊天 + 系统消息 + 转写按时间排序、字段统一 | 用例 + 真机 |
| E5 | 前端默认开启 + 一次性告知条 + 一键关闭（关闭后不再上传） | 真机 DOM/网络 |
| E6 | 转写气泡样式（麦克风图标 + 说话人 + 时间）与聊天可区分 | 真机截图 |
| E7 | 纪要素材含转写：生成纪要时带上转写文本 | 用例 + 真机纪要含语音内容 |
| E8 | 门禁：`pytest` / `smoke` / `tsc` / `build` | 门禁输出 |

## 5. cp 切分

| cp | 内容 |
| --- | --- |
| cp-0 | 本文 + 函数级 design + ADR-0022 + 台账 |
| cp-1 | 迁移 + `services/stt.py`（唯一出口，可注入打桩）+ `repositories/transcripts.py` + 上传/列表路由 + 用例 |
| cp-2 | 三源合一：`build_conversation` + `GET /conversation` + 前端 `ConversationPanel` |
| cp-3 | 前端采集：`useTranscription`（默认开启 / 8 秒分段 / 静音跳过 / 关闭即停）+ 告知条 + 开状态接口 |
| cp-4 | 纪要接上转写素材 |
| cp-5 | 收官（真机取证：说一句话 → 8 秒后气泡出现 → 生成纪要含该句 + 门禁 + 文档 + review） |

## 5.1 依赖登记（2026-09-20，实现期）

| 依赖 | 用途 | 处置 | 出处 |
| --- | --- | --- | --- |
| `python-multipart==0.0.32` | FastAPI 解析前端上传音频的 multipart 表单（B 路径用；A 路径不再需要） | **已装**（conda `learningguide`）+ 追加进 `backend/requirements.txt`；按 `cr-01.md` 的建议值执行（超时 defaulted，你可否掉） | `docs/rounds/r010-transcription/cr-01.md` |
| `livekit-agents`（+`livekit-api`） | 转写 worker（A/C 路径识别侧） | **装在独立环境 `lg_agents`**（**不进** `learningguide` 主环境）；清单落 `backend/requirements-agents.txt`（cp-2w 产出） | `cr-02.md`、`spike-01-path-a.md` §3-1（安装 37.6s） |

## 6. 文档产出清单（覆盖矩阵）

| 件套 | 页 | 路径 | 状态 |
| --- | --- | --- | --- |
| 需求单 | 本页 | `docs/00-requirements/r010-transcription.md` | landed |
| A 设计页 | 函数级设计 + **§3.2 视觉契约** + **§5 教学契约** | `docs/rounds/r010-transcription/design.md` | landed（契约两节于 cp-0b 补齐） |
| 口径 | **界面口径卡七项** | 本页 §2.1 | landed（cp-0b 补齐） |
| B 实现同步页 | 轮次台账 | `docs/rounds/r010-transcription/changes.md` | **landed**（cp-1~cp-5 全落） |
| B 实现同步页 | 审查报告 | `docs/rounds/r010-transcription/review.md` | **landed**（cp-5 定稿） |
| 决策 | ADR-0022（路径 B + 官方协议迁移点） | `docs/03-decisions/ADR-0022-transcription-path.md` | landed |
| 调研 | 两条调研（客户端转写事件 / Agents 侧与 Jitsi 对照） | `docs/rounds/r010-transcription/research-01/02.md` | landed |
| CR | 依赖登记（L3） | `docs/rounds/r010-transcription/cr-01.md` | landed |
| CR | **换轨（L3，proposed）** | `docs/rounds/r010-transcription/cr-02.md` | **待你批** |
| Spike | 路径 A 实测（含配额与成本） | `docs/rounds/r010-transcription/spike-01-path-a.md` | landed |
| 决策 | **ADR-0023（换轨，proposed）** | `docs/03-decisions/ADR-0023-agent-side-transcription.md` | 待你批 |
| 模块轴 | 实现页 + 功能页（转写 / 三源合一） | `docs/02-modules/r010-transcription{,-features}.md` | **未做**（转写行为已在 design §9 + 教学页写清；见 review 未闭合 ⑥） |
| C 使用者教学页 | 「说的话变成文字、进纪要」怎么用（含演示前置与探活、免费档限制） | `docs/tutorials/r010-transcription-user-guide.md` | **landed**（cp-5） |
| 索引轴 | 需求索引 / `docs/README.md` / roadmap / 教学页索引 回填 | 四处 | **landed**（cp-5） |
| D 开发者教学页 | **不适用**：本轮的扩展点已在 design §2.3（STT 唯一出口、可换供应商）写清，且 `r002-livekit-dev-guide` 已覆盖「自助加能力五步」；如需单独页，请在收官时点名 | — | 不适用（理由如上） |
| README / `.env.example` | `.env.example` 三新键 + 演示路径（说话 → 气泡 → 纪要） | 两处 | **landed**（`.env.example` 已改；演示路径见教学页 §4） |

## 7. 变更记录

| 日期 | 版本 | 改了什么 | 依据 |
| --- | --- | --- | --- |
| 2026-09-19 | v1 | 建页：R1~R6 + 口径与边界 + E1~E8 + STT 方案 + cp 切分 | 澄清单 Q1~Q12（你 2026-09-19） |
| 2026-09-20 | v2 | 补 **§5.1 依赖登记**（`python-multipart`，CR r010-01）与 **§6 覆盖矩阵**；`STT_*` 三键状态改为「已进 `.env.example`，值待填」 | 本轮 cp-1 实现期实测 + 铁律 6（覆盖矩阵） |
| 2026-09-20 | v3 | 补 **§2.1 界面口径卡七项**（你回 Q1=①）；覆盖矩阵同步 | 你 2026-09-20「1」（Q1=①）；设计契约要求 |
| 2026-09-20 | v7 | 收官：全部覆盖矩阵转 `landed`（模块轴如实标未做）；验收对账见 `review.md`（E1~E14） | cp-5 收官实测 |
| 2026-09-20 | v6 | 界面细节随换轨同步（只读状态 chip + 告知条按钮与文案）；覆盖矩阵 E4/E5/E13 状态更新 | cp-3a/cp-3b 实现 + 界面契约要求 |
| 2026-09-20 | v5 | **换轨定案**：CR-02 / ADR-0023 转 `accepted`（你「按你想的来」授权）；隐私口径变化不再阻塞（媒体本经 LiveKit Cloud）；**确立"验证期零配额"纪律**（桩 + 假 STT） | 你 2026-09-20 原话 |
| 2026-09-20 | v4 | **换轨**：R1/R6 口径改写（关麦即不转写、隐私措辞如实）；§5.1 补 worker 依赖（独立环境）；覆盖矩阵补 CR-02/ADR-0023/spike-01；E 条目修订见 design §9.7 | 你 2026-09-20「有免费档就行，只做最小程度演示，出设计方案」+ spike-01 实测 + ADR-0023 |
