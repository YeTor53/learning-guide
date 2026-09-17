---
title: ADR-0001 自建 LiveKit 替代 LiveKit Cloud
description: 决定用官方 livekit-server 的 Windows 原生二进制在本机自建服务，替代题面建议的 LiveKit Cloud。
type: reference
status: accepted
owner: 陀梓皓
updated: 2026-09-16
---

<!-- overview -->
记录「LiveKit 从哪来」这一决策：为什么不用题面建议的 LiveKit Cloud，自建的代价与边界是什么。

## 背景

- 题目 A 的技术建议写的是「LiveKit Cloud + 任意 LLM API」，属建议而非硬性要求；硬性要求是「服务端签发 Token、Secret 不得进入前端或仓库」。
- 用户拍板 P3=B：自建。
- 起点实测（2026-09-16）：本机无 Docker、WSL 无发行版、Hyper-V 未启用；官方 `livekit-server v1.13.7` 发布物含 Windows 原生二进制；`livekit-server-sdk 2.19.0` 在 npmmirror 可取。

## 决策

用官方 `livekit-server` 的 **Windows 原生二进制**在本机运行 LiveKit 服务（含 API Key/Secret 由本机配置生成），应用服务端用 `livekit-server-sdk` 签发 Token 与调用 RoomService；**不依赖 Docker，也不依赖外部账号**。

## 理由

1. **零外部依赖**：不需要注册账号、不需要外部服务可达性，评审与自查都在本机闭环。
2. **自建比 Docker 更省**：Windows 原生二进制直接运行，绕开 WSL2/Hyper-V 补装与重启（本机不具备这两个前提）。
3. **可复现性更强**：配置文件与启动命令随仓库提交，任何人（有 Windows 机器）都能起同一份服务。
4. **不影响必做项验收**：题面所有 LiveKit 相关硬性要求（服务端签 Token、Secret 不进前端、服务端踢人）自建同样满足甚至更易证明。

## 被否的替代方案

- **LiveKit Cloud 免费项目**（题面建议）：需要注册账号与外部服务；本机 Python 侧证书库损坏、无凭据，环境风险集中在一个不可控外部依赖上。作为**回退方案**保留（ADR 变更后启用）。
- **Docker 自建 LiveKit**：本机 WSL2/Hyper-V 均不具备，补装 + 重启的成本与风险高于收益；Docker Compose 降级为 M5 加分项（只交文件 + 说明，不阻塞必做闭环）。
- **自研音视频传输**：与题面要求不符，工作量不可接受。

## 影响

- `.env` 中 `LIVEKIT_URL` 指向本机服务（`ws://localhost:7880`），`LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` 由本机 `livekit.yaml` 定义。
- 设计说明中需写入「为什么自建、怎么起、与 Cloud 的差异（无 TURN/无公网/单节点）」。
- 演示限定在**本机 localhost 多浏览器**；公网部署不在本轮范围。
- 端口占用与进程生命周期由项目脚本管理（起服务 / 停服务），须在 README 写明。

## 后果与待办

- **待验证（M2 第一轮必做）**：本机起 `livekit-server` 后，浏览器经 `localhost` 能否完成「加入房间 + 麦克风/摄像头 + 屏幕共享」最小闭环。验证不通过则改回 LiveKit Cloud，并在本文件追加「变更记录」。
- M2 验收证据需包含：服务进程输出、服务端签发 Token 的调用结果、双浏览器同房的实际画面。
- Chrome 对 `localhost` 视为安全上下文，`getUserMedia` / `getDisplayMedia` 无需 HTTPS；此点需在验证轮实测确认。

## 变更记录

- 2026-09-17 **降级为离线兜底方案**：P3′ 复评（ADR-0003）决定「Cloud 为主 + 自建脚本留档」，本 ADR 的自建路径不再是主路径，改为演示降级/离线方案保留；决策内容本身仍然有效（本机自建可行且不需要 Docker，已实测）。
