---
title: r010 调研 02：开源实现与官方算法细节（Jitsi / LiveKit Agents / 协议字段）
description: 已抓到的三条硬参考：Jitsi 桥接式转写架构、LiveKit Agents 的转写模块与 synchronizer、TranscriptionSegment 字段；含剩余未取到项与原因。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
接 `research-01.md`。本轮把「开源实现参考 / 协议字段 / 官方算法」补上；**没取到的（中文流式服务价格、Zoom/Meet 隐私文案原文）如实写在 §4，并说明取不到的原因**（本机 bing 返回无关结果、DuckDuckGo 与 r.jina.ai 被墙、猜的 doc 路径 404）。

## 1. Jitsi：桥接式转写（业界成熟做法，最有参考价值）

来源：[jitsi.github.io/handbook/docs/devops-guide/transcription/](https://jitsi.github.io/handbook/docs/devops-guide/transcription/)（HTTP 200，原文已抓）

- 架构：`participant audio —Opus→ JVB（视频桥）—WebSocket→ 转写服务 →（OpenAI / Deepgram / Google Gemini / xAI）`；转写结果**流回并注入会议**（injected into the conference）。
- 服务是**桥侧**的（JVB 把每个人的 Opus 音频转发给转写服务），参考实现 `opus-transcriber-proxy`；**旧的 Jigasi 方案已废弃**，官方要求新部署用桥接式。
- **开关由信令层决定**：Jicofo 决定何时开启转写并告诉桥连哪个 URL；客户端 `config.js` 里开启 → 也就是「**房间级开关 + 服务端下发**」。
- **对我们的启示（写进设计）**：
  1. 「谁在说」由**服务端按音轨**归属，不靠前端猜 —— 我们走路径 B（本端上传）时，说话人就是上传者本人，天然正确；这也说明**如果哪天上路径 A，归属问题由 LiveKit 的 participant/track 身份解决**。
  2. 「转写结果注入会议」是标准做法：Jitsi 注入**字幕/聊天**，我们要注入**讨论流**（= 你的「并入文字对话」）✓ 方向一致。
  3. 开关分层（房间级 + 客户端）值得借鉴：你的「默认开启」是客户端层，房主层可以后续再加。

## 2. LiveKit Agents：官方转写模块与 partial/final 同步器

来源：GitHub API 列 `livekit/agents` 仓库树（HTTP 200，已抓）

- 示例：`examples/other/transcription/multi-user-transcriber.py`（**多用户转写器**，正是「一间房多个说话人」的场景）。
- 实现：`livekit-agents/livekit/agents/voice/transcription/` 下有 **`synchronizer.py`**（同步器）、`filters.py`、`text_transforms.py`、`_speaking_rate.py`、`_utils.py`。
- **对我们的启示**：**partial → final 的对齐/替换是官方要专门写一个 synchronizer 来解决的问题** → 说明我「中间稿不落库、只落最终稿；前端原地替换」的取舍是对的，且如果以后要走路径 A，这块**直接复用官方模块**，不用自己造。

## 3. 协议字段：`TranscriptionSegment`

来源：`raw.githubusercontent.com/livekit/client-sdk-js/main/src/room/types.ts`（HTTP 200，已抓）

```ts
export interface TranscriptionSegment {
  id: string;
  text: string;
  language: string;
  startTime: number;
  endTime: number;
  final: boolean;
  firstReceivedTime: number;
  lastReceivedTime: number;
}
```

要点（按字段）：`id`（同一段话的稳定标识 → **原地替换的键**）、`text`、`startTime`/`endTime`、`final`（**false=中间稿，true=最终稿**）、`language`。这正是「并入对话」要的三个信息：谁说（来自 participant）、说了什么（text）、是不是定稿（final）。

## 4. 本轮**没取到**的（如实 + 原因）

| # | 项 | 为什么没取到 | 下一步怎么取 |
| --- | --- | --- | --- |
| 1 | 官方文档正文（events / agents Text & transcriptions） | 页面 JS 渲染，纯 HTTP 抓取拿不到正文 | 用本机 Playwright 打开读 DOM |
| 2 | 中文实时转写服务（火山/讯飞）的流式接口与计费 | 猜的文档 URL 404；bing 在本机返回无关结果（被降级） | 先只按「硅基流动 Whisper 兼容 REST」这个已知可达的口径设计（`/audio/transcriptions`），流式留作补充调研 |
| 3 | Zoom / Google Meet 的转写隐私告知原文 | 同上（搜索结果无效、支撑页需登录） | 用 Playwright 抓 support 文档；或直接按 §1 的「房间级开关 + 明确告知」自行定稿措辞 |
| 4 | 开源项目里「转写与聊天同流」的具体表结构 | 搜索结果无效 | 以 Jitsi（注入会议）+ LiveKit（segment 契约）两条为准自定模型，见 research-01 §3 |

## 5. 调研阶段结论（可直接进设计）

1. **协议用官方的**：`TranscriptionSegment`（id/text/times/final/language）+ `RoomEvent.TranscriptionReceived`；不自造。
2. **本轮走路径 B**（本端采集 → 我方后端 STT → 落最终稿 → 并入讨论流），**在 ADR 写清路径 A（Agents 侧转写）的迁移点**：换轨时把「本端上传」换成「Agent 发 segment」，前端的接收与渲染层**不用改**。
3. **中间稿不落库**；前端按 `id` **原地替换**，`final=true` 才固化成一条对话消息（按 Jitsi「注入会议」的口径）。
4. **开关分层**：本轮只做客户端层（默认开启 + 一次性告知 + 一键关），房主层留接口。
