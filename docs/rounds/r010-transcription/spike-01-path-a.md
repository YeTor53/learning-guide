---
title: r010 Spike 01：路径 A（LiveKit Agents 侧转写）实测报告
description: 独立环境实测——派单/多用户注入房间/归属/渐进字幕/延迟/真语音识别/资源占用，附复现命令与三种落地选项。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-20
---

<!-- overview -->
你 2026-09-20：「那就测试一下A」。本页是**一次性 spike 的实测报告**（按 spike 规矩：代码为一次性产物，不进主线）。
**主线零改动**：依赖装在独立 conda 环境 `lg_agents_spike`，代码与日志全在 `%TEMP%\lg_r010_spikeA\`，仓库本轮只新增本页与台账两行。

## 1. 测了什么（两个问题，按风险排序）

| # | 问题 | 结论 |
| --- | --- | --- |
| 010-01（高风险） | Agents 侧能否把**多个参与者**的话注入房间、被 `livekit-client` 收到、且**能分辨谁说的** | **通过**（见 §3 证据 2~4） |
| 010-02（中） | 安装/运行成本（依赖、进程、内存、延迟） | **有数**（见 §3 证据 1/5/6） |

## 2. 做法（可复现）

环境：独立 conda 环境 `lg_agents_spike`（Python 3.11.16），只装 `livekit-agents` + `livekit-api`；用仓库 `.env` 的 LiveKit Cloud 凭据（`LIVEKIT_MODE=cloud`，`region=Japan`），**凭据只进子进程环境，未回显、未入库**。

三段脚本（一次性，全在 `%TEMP%\lg_r010_spikeA\`）：

| 脚本 | 作用 |
| --- | --- |
| `worker_fake_stt.py` | `AgentServer` + `@server.rtc_session(agent_name="spike-transcriber")`；**每个远端参与者一个 `AgentSession`**；STT 可切两种：`SPIKE_STT=fake`（离线假 STT，验证管线）/ `inference`（官方 `inference.STT("deepgram/nova-3")`，验证真识别） |
| `mint.py` | 用 `livekit-api` 建房（`CreateRoomRequest(agents=[RoomAgentDispatch(agent_name=...)])`）并签发 3 个 token（pub1/pub2/观察员） |
| `drive.py` | Playwright 起 3 个 Chromium（前两个发布麦克风，用 `--use-file-for-fake-audio-capture=<本机离线TTS生成的中文WAV>` 当音源），页面用仓库同一份 `livekit-client` 监听 `RoomEvent.TranscriptionReceived` |

真语音来源：Windows 内置离线语音 `Microsoft Huihui Desktop (zh-CN)` 合成「今天我们先讲第一章 线性回归的基本思想」→ 214,482 字节 WAV。

## 3. 实测证据（数字原样来自日志与报告 JSON）

1. **安装与运行成本**：`conda create` 39.6s；`pip install livekit-agents livekit-api` **37.6s**（约 60 个包：`livekit-agents 1.8.2` / `livekit-api 1.2.1` / `av 18.1.0` / `numpy 2.4.6` / `grpcio` / `opentelemetry` 等）。worker 跑起来后：**1 个进程、RSS 429 MB**（含预载 `av` 与本地推理模型）、管理用 HTTP 端口 `:2077`。附带发现：**dev 模式已废弃**（日志警告建议改用 `lk agent dev`）。
2. **派单/进房**：worker 注册后日志 `registered worker {"agent_name": "spike-transcriber", "region": "Japan"}`；建房带 `RoomAgentDispatch` → 日志 `被派单进房: room=spike-a-1789871110`；**worker 重启后对同一已建房再次自动派单**（无需重建房）。
3. **多用户注入房间（核心问题）**：45 秒里三个客户端各自收到 **56~58 条**转写事件；`listener` 端来源统计 `{pub1: 30, pub2: 26}` —— **一个人的话会送到其他所有人**；`pub1` 端 `{pub1: 32, pub2: 26}`（自己的话也回流）。worker 侧对每个远端参与者**各开一个 session**（日志 `开 session: pub1/pub2/listener`），每个 session 各订到对应音频轨（`track_subscribed kind=1 from=pub1/pub2`）。
4. **归属可辨**（这条此前标"未核实"）：客户端回调**第二个参数就是 `Participant`**，`identity` 可直接取到（页面 dump 出 `seg<pub1>` / `seg<pub2>`），无需靠猜。
5. **渐进字幕（B 路径没有的能力）**：同一条 STT 输出在前端表现为 **`final=false` 的渐进片段 → `final=true` 的定稿**（示例：`一章` → `第一章线性回归等` → `第一章线性回归的基本思想`），即官方 `synchronizer` 直接给了"逐字上屏"。
6. **延迟（端到端，含 LiveKit Cloud 日本节点往返）**：假 STT 模式 22 条配对样本 **中位 257~267ms、最小 254ms、最大 1170~2426ms**；真 STT 模式官方日志自带 `transcript_delay: 0.5516s`。
7. **真语音识别（真 STT 全链路）**：`inference.STT("deepgram/nova-3")` **直通**——**无需我们自备 STT key**（走 LiveKit Cloud Inference）；识别结果「今天我们先讲第一张线性回归的基本思想。」（TTS 同音字「章」→「张」，其余准确），三端都收到。
8. **边界（如实）**：① 不发麦克风的观察者**不产生**房间转写，但 worker 仍为它建了 session（空转，属可优化点）；② 全程无 `ERROR`/异常；③ **未测**：8 人满员、worker 掉线/重启中断、长时（>1 小时）稳定性、计费与配额。

## 4. 对 A/B 对比的修正（我此前有两处估计偏保守）

| 我此前的说法 | 实测修正 |
| --- | --- |
| 「A 要额外 STT 插件与 key 管理」 | **不需要自备 key**：官方 Inference 直通本项目 Cloud 账号，`inference.STT("deepgram/nova-3")` 即用 |
| 「A 的实时性只是理论上更好」 | 实测端到端 **中位 ~257ms**（假 STT）/ 官方 `transcript_delay 0.55s`（真 STT），且**天然带渐进字幕**；B 是 8 秒分段 + 识别，端到端 ~9~11 秒 |
| 「A 前端成本中」 | 若走 A，前端**省掉** MediaRecorder 分段、重传、静音门限、关即停这一整套（cp-3 的大部分工作量），只剩"监听 + 渲染" |
| 仍然成立的成本 | **多一个常驻进程**（实测 429MB，需随演示/部署一起起）、**单点故障**（worker 掉线即全场无转写）、**音频经 Cloud 与供应商**（B 是音频只到我方后端）、以及"房间真相 vs 我方 HTTP 落库"的**双通道**问题（要进纪要就得把 final 段落到我们库里） |

## 5. 三种落地选项（等你拍板；换轨 = 设计变更，按 CR 走）

| 选项 | 识别在哪 | 我们的库怎么来 | 实时感 | 新进程 | 主要代价 |
| --- | --- | --- | --- | --- | --- |
| **A 纯** | Agent worker（Inference 或自带 key 的插件） | 前端把 `final` 段 POST 到我们后端落库（一条文本、KBs 级） | 最好（渐进字幕 + 0.55s） | 1 个（429MB） | 演示/部署多一件东西；worker 掉了没转写 |
| **C 混合（推荐）** | 同 A | 同 A（**复用已完成的 cp-1 转写表与接口**，接口从"传音频"改成"传文本"，STT 参数从后端移到 worker 侧） | 同 A | 1 个 | 同 A；但保留"HTTP 落库为唯一真相"，与 r004~r009 架构一致 |
| **B 原设计** | 我方后端（`services/stt.py`） | 前端上传音频 → 后端转写 → 落库 | 8 秒一段（~9~11s 延迟，无渐进） | 0 | 前端要写的分段/重传/门限全在；但离线可打桩、答题场景最稳 |

**我的建议**：**C**。理由：① A 的两个"硬优势"（真实时、归属天然、渐进字幕）实测兑现，且**不需要新 key**；② C 用前端回传文本的方式，**保住**我们"HTTP 落库为唯一真相 + 可离线打桩 + 与既有架构一致"的三条底线，`cp-1` 已完成的表/幂等/可见性全部复用；③ 唯一剩下的硬成本是那一个常驻 worker——`dev.bat` 里加一行即可，答辩前先 `curl` 探活。
若你更看重"演示绝对不出意外、零新进程"，则维持 **B**（本轮设计原文），把 A/C 记为加分项。

## 6. 复现（全程只读仓库、不改主线）

```bash
conda create -n lg_agents_spike python=3.11 -y
# 注意：本机阿里云镜像实测 25 KB/s，官方源 22.6 MB/s —— 用官方源（慢镜像会把这件事拖成 40 分钟）
pip install livekit-agents livekit-api -i https://pypi.org/simple/ --trusted-host pypi.org --trusted-host files.pythonhosted.org
python %TEMP%\lg_r010_spikeA\worker_fake_stt.py dev        # SPIKE_STT=fake|inference
python %TEMP%\lg_r010_spikeA\mint.py [房间名]              # 建房 + 派单 + 发 token（写 tokens.json）
C:\ProgramData\miniconda3\python.exe %TEMP%\lg_r010_spikeA\drive.py   # Playwright 三端取证
```

## 7. 变更记录

| 日期 | 版本 | 改了什么 | 依据 |
| --- | --- | --- | --- |
| 2026-09-20 | v1 | 建页：两个问题 + 8 条实测证据 + A/B 对比修正 + 三种落地选项 | 你 2026-09-20「那就测试一下A」；本轮实测日志与报告 JSON |
