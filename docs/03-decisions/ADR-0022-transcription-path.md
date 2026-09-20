---
title: ADR-0022 转写走本端采集 + 自有后端 STT（路径 B），并用官方 TranscriptionSegment 契约留迁移点
description: 为什么不用 LiveKit Agents 侧转写、为什么只落最终稿、隐私与开关分层的取舍。
type: reference
status: accepted
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
背景：用户要求「转写默认开启 + 说的话并入文字对话 + 含成员进出等管理信息」，并先做 STT 获取方案调研。调研见 `docs/rounds/r010-transcription/research-01/02.md`。

## 事实（调研已证）

1. `livekit-client` **2.22.3** 自带 `RoomEvent.TranscriptionReceived`（@beta）与 `TranscriptionSegment`（`id/text/language/startTime/endTime/final/firstReceivedTime/lastReceivedTime`）→ 转写协议**不用自造**。
2. 官方 **Agents 侧转写**存在且成熟：Agent 做 STT 时**转写实时发布到前端**，`AgentSession` 默认开启；仓库里有 `examples/other/transcription/multi-user-transcriber.py` 与 `voice/transcription/synchronizer.py`（partial/final 对齐是专门模块）。
3. **Jitsi** 的成熟做法是桥侧转写（JVB → WebSocket → 转写服务 → 结果注入会议），开关由信令层决定（房间级 + 客户端），旧 Jigasi 方案已废弃。

## 决定

### D1 本轮走**路径 B**：本端麦克风采集 → 自有后端 → STT → 只落最终稿 → 并入讨论流

理由：① 功能本体（并入对话 + 与系统消息同流 + 进纪要）与传输通道**解耦**；② 可**离线打桩**（`call_stt(client=...)`），演示不依赖第三个进程与外部网络；③ 与本项目既有架构一致（HTTP 落库为唯一真相，DataChannel/轮询只做加速）。

### D2 **协议按官方口径**，因此路径 A 可无缝迁移

- 落库 `transcripts.id` = segment 稳定 id、`final` 字段保留；前端按 `id` 原地替换、`final=true` 才固化。
- **迁移点**（写死在设计里）：把「本端上传音频」换成「Agent 发布 segment」，前端 `transcriptionReceived` 监听 + `ConversationPanel` 渲染层**零改动**。

### D3 **只落最终稿**，中间稿不落库

理由：避免库里堆满被替换掉的半句；也与官方 `synchronizer` 的职责划分一致（同步/替换在传输层做，落库只存结论）。代价：本轮前端不做中间稿字幕（`final=false` 的实时上屏归加分项）。

### D4 开关分层：本轮只做**客户端层**，房主层留接口

- 客户端：进房一次性告知 + 默认开启 + 一键关闭（关闭即停传）；`localStorage` 记住「本人关闭过」。
- 房主层（本轮不做）：`rooms` 上加一个房间级开关即可，接口留 `GET /stt/status` 里带 `roomEnabled` 字段的位置。

### D5 隐私：**不保留原始音频**

音频只在内存里过一遍（上传 → STT → 丢弃）；日志不记文本；转写文本可见范围 = 本房全员（会议记录本质上是公开的）。

## 备选与否决

| 备选 | 否决理由 |
| --- | --- |
| 直接上 LiveKit Agents 侧转写 | 要多跑一个常驻 worker、要额外 STT 插件与 key 管理；演示与部署成本明显上升，而功能本体不需要它 |
| 中间稿也落库 | 库里会出现大量被替换的碎片；查询/纪要都要额外过滤 |
| 用 Web Speech API 前端直转 | 中文质量与可复现性不可控，且无法统一落库 |
| 保留原始音频供回听 | 存储与合规成本高；用户口径只要文字 |
