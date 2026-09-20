---
title: r010 调研 01：实时转写的官方能力与两条实现路径
description: 已实测的事实（LiveKit 客户端原生转写事件 / Agents 侧转写 / 网络可达性）+ 两条架构路径对比 + 还需补查的清单。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
你要求「先搜索相关项目做参考，这个挺难，要严格做好设计」。本页是**第一轮调研的事实记录**（只写查到的、标明来源；没查完的单列在 §5）。结论会改 `redirect-01.md` 的 Q1/Q2 建议值。

## 1. 已证实的关键事实（含来源）

### 1.1 LiveKit **客户端 SDK 自带转写事件**（本项目已装 2.22.3）

- 来源：`frontend/node_modules/livekit-client/package.json`（版本 **2.22.3**）+ 本机 `dist/**` 符号扫描 + GitHub 源码
  [`client-sdk-js/src/room/events.ts`](https://raw.githubusercontent.com/livekit/client-sdk-js/main/src/room/events.ts)、
  [`.../participant/Participant.ts`](https://raw.githubusercontent.com/livekit/client-sdk-js/main/src/room/participant/Participant.ts)
- 事实：
  - `RoomEvent.TranscriptionReceived = 'transcriptionReceived'`（SDK 注释标 **@beta**），回调签名
    `(transcription: TranscriptionSegment[], publication?: TrackPublication) => void`；
  - `Participant` 上的 `transcriptionReceived` 回调、`TranscriptionSegment` 类型在 `Room.d.ts` / `Participant.d.ts` / `TrackPublication.d.ts` 均有；
  - 2.22.3 的 `attribute-typings.d.ts` 里还有 **`lk.transcription`** 属性（LiveKit 的 text-stream 通道）。
- **含义**：转写「谁在说、说了什么、是不是最终稿」这套协议**不用我自己发明** —— 客户端本来就认得；服务端只要有人把 `TranscriptionSegment` 发进来即可。

### 1.2 官方有「Agents 侧转写」路径

- 来源：[docs.livekit.io/agents/build/text/](https://docs.livekit.io/agents/build/text/)（页面标题即「Text and transcriptions」，属 Build Agents → Multimodality）、以及
  [`livekit/agents` README](https://raw.githubusercontent.com/livekit/agents/main/README.md)（PyPI 包 `livekit-agents`，定位「服务器上跑的实时可编程参与者」）。
- **含义**：官方路子是**让一个 Agent 进房间**，用 STT 插件做识别，再把转写发回房间；客户端用 §1.1 的事件接收。

### 1.3 本机网络现实（决定调研手段）

| 站点 | 可达 | 用途 |
| --- | --- | --- |
| `docs.livekit.io` | ✅ 200 | 官方文档（部分页是 JS 渲染，纯抓取取不到正文） |
| `raw.githubusercontent.com` | ✅ 200 | 读官方源码/README（**最可靠的参考来源**） |
| `github.com` | ✅ 200 | 仓库页 |
| `cn.bing.com` / `baidu.com` | ✅ 200 | 中文检索 |
| `html.duckduckgo.com` | ❌ 超时 | 原计划的主检索不可用 |
| `r.jina.ai`（网页转 markdown 代理） | ❌ 超时 | 正文抓取代理不可用 |

## 2. 两条实现路径（这是本轮要拍板的核心）

| 面 | **路径 A：LiveKit 原生转写（Agent 侧）** | **路径 B：本端采集 + 自有后端 STT** |
| --- | --- | --- |
| 谁做识别 | 一个 `livekit-agents` worker 进房间，用 STT 插件识别各轨 | 每个客户端自己录自己（MediaRecorder/AudioWorklet）→ 上传到我方 `/api/stt` |
| 分发通道 | **LiveKit 自带**（`TranscriptionReceived` / `lk.transcription` 文本流） | 我方的 HTTP 落库 + DataChannel 广播（沿用 r004~r009 那套） |
| 前端成本 | 中（接官方事件、渲染 segment；SDK 已装） | 中高（分段、重传、时序拼接、说话人归属都要自己写） |
| 后端成本 | 中（多一个常驻 worker、要配 STT 插件） | 低（一个 POST 接口 + 表） |
| 演示成本（面试） | 高（要跑第三个进程；本地/云都要 STT key） | 低（我方可离线打桩，演示最稳） |
| 与「并入对话 + 管理信息」的契合 | 好（转写天然带 participant + track + 时间） | 好（落库后与聊天/系统消息同流可控性更强） |
| 失效模式 | worker 掉了就没转写（要监控） | 上传失败要重试；说话人＝本人（无跨端归属问题） |
| 官方口径 | **官方推荐** | 自造轮子，但可控 |

**我的建议**：**先用路径 B 把「转写并入对话 + 系统消息同流 + 纪要接入」做完整（这是你要的功能本体，且能离线打桩、真机好验）**；同时**在 ADR 里写清路径 A 的迁移点**（`TranscriptionSegment` 契约与 `TranscriptionReceived` 事件接进来即可换轨），并把它作为「加分/后续」列在文档里。理由：功能本体与通道解耦；A 的额外进程会显著抬高演示与部署成本，而本项目其余部分（等候室/焦点/纪要）都在自有后端上，B 与现有架构一致。

## 3. 数据模型（调研后仍成立的两条）

- 你要求的「并入文字对话」= 三源合一：`chat_messages(kind='chat'|'system')` + 语音文本。两条存法：
  - **② 独立 `transcripts` 表 + 查询合并**（我在 Q2 的建议）：不污染现有聊天表；合并层要处理排序键、分页、「加载更早」、结束后只读。
  - ① 直接进 `chat_messages` 加 `kind='speech'`：查询层最省，但会把「重传/修正中间稿」这类转写特有语义塞进聊天表。
- 转写特有语义（**无论哪条路径都要处理**）：同一段话会有 **中间稿（partial）→ 最终稿（final）**；显示上要原地替换而不是追加两条；`TranscriptionSegment` 里本来就有 `final` 标记（见 §1.1），这一点官方协议已经考虑到了。

## 4. 对 Q1/Q2 的修订建议

| # | 原建议 | 调研后 |
| --- | --- | --- |
| Q1 STT 主方案 | ① 云端 Whisper 兼容 | **仍是 ①**，但把「LiveKit 原生/Agents」单列成 Q1b：本轮是否同时接；我建议**本轮不接**（见 §2 建议） |
| Q2 落库方式 | ② 独立 `transcripts` 表 + 合并 | **不变**，并补一条：中间稿不落库，只落最终稿（避免库里堆一堆被替换掉的半句） |

## 5. 还需补查的（下一轮调研，我已知道去哪查）

1. **官方文档正文**：`docs.livekit.io/home/client/events/`、`/agents/build/text/` 是 JS 渲染，纯抓取拿不到正文 → 改用 Playwright 打开并读 DOM（本机已有 Playwright）。
2. **`TranscriptionSegment` 字段细节**：直接读 `raw.githubusercontent.com/livekit/client-sdk-js/main/src/room/types.ts`（或 `dist` 里的 `.d.ts`，本机就有）。
3. **开源实现参考**（用于对照数据模型与 UX）：Jitsi 的转写/字幕架构、以及「转写与聊天同流」的既有实现；检索走的 `cn.bing.com`（结果页结构待解析）。
4. **中文实时转写服务**（若走路径 B 的流式档位）：硅基流动（Whisper 兼容 REST，本机已能连通）、火山引擎/讯飞的 WebSocket 流式接口与计费。
5. **隐私 UX 样板**：Zoom / Google Meet「开始转写时的全员告知 + 主持人控制」的具体措辞与交互。
