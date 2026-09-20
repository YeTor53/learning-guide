---
title: r013 变更台账
description: 演示就绪五项（焦点修复 / 强停共享取证 / worker 自愈 / 结束房回看 / 大屏进抽屉）的逐 cp 提交、用户消息与决策登记。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-20
rounds: [r013]
---

<!-- overview -->
一个提交 = 一个逻辑增量；提交信息 `type(scope): ≤50字 [Req: r013]`。

## 1. cp 提交台账

| cp | 提交 | 内容 | 测试/证据 | 文档 |
| --- | --- | --- | --- | --- |
| cp-r013-1 | 文档先行 | 需求单（含断线方案 §10.5）+ 逐文件函数级设计 + 台账骨架 | 不适用（纯文档） | 需求单、design |
| cp-r013-4 | 本次提交 | C 项：worker 自愈与可观测——新增纯函数 `backend/agents/retry.py`；`transcriber.entrypoint` 的连接段改为**有限重试（3 次 / 2+4 秒退避）**，彻底失败时上报原因并以**退出码 2** 退出（不再裸崩）；心跳带 `lastError`，后端 `/rooms/{id}/stt-status` 透出，控制坞芯片 hover 可见 | 用例 **+6**（`test_connect_retry.py` 5 条 + `test_stt_heartbeat.py` 1 条）→ `pytest 208 passed`；`tsc`/`build` 绿；真机：芯片 title 出现/清除「最后错误」各一次 | r010 模块页变更记录、roadmap §9 |
| cp-r013-3 | 本次提交 | B 项：新增 `frontend/scripts/verify-screen-force-stop.py`；真机取证「A 不点停止、直接关标签」→ B 端清格 | **两次实测均 0.5 秒**清格、宫格恢复 1 格；实现无需改动（`useScreenShare` 既有 `TrackUnpublished`/`ParticipantDisconnected` 重扫就够）；**边界**：手段=WS 正常关闭，网络级硬断未测 | `docs/02-modules/r004-room-extras.md` §11 遗留 4 回填 |
| cp-r013-2 | 本次提交 | A 项：新增 `frontend/scripts/verify-focus-three-way.py`（三隔离 Chrome 真跑三人档「给焦点」）；**在当前代码不复现** r009.5 登记的现象 | **PASS 8/8 ×3 次**（三端 `mode=focus`、焦点格各 1、焦点 identity 三端一致）；顺带实测：举手传播到另两端 **2.0 秒**、服务端 1 条；脚本自身踩坑三条已写进头部注释（禁用按钮点击无效 / CDP keepalive ping 超时 / 各端排序「本地优先」不能比首项） | `docs/02-modules/r009-focus-system.md`、roadmap §9 |

## 2. 缺陷与例外登记

（待填）

## 3. 用户消息与决策

| 日期 | 消息/决策 | 落点 |
| --- | --- | --- |
| 2026-09-20 | 「把到 6 的都做了，然后这个断线的测试给我个方案」→ 按编号回读：① 焦点 ② worker ③ 断线（只要方案）④ 强停共享 ⑤ 回看页 ⑥ 大屏进抽屉 | 需求单 §1、§10.5 |

## 4. 变更记录

| 日期 | cp | 变更 | 依据 |
| --- | --- | --- | --- |
| 2026-09-20 | cp-1 | 建台账 | 需求单 v1 |
| 2026-09-20 | cp-4 | C 项结论：自愈（重试 + 退出码 2）+ 可观测（lastError 到芯片）；**FFI panic 根因未修**（需升级 `livekit-agents`，你未批） | 用例 + 真机 |
| 2026-09-20 | cp-3 | B 项结论：强停共享 0.5 秒清格（标签关闭路径），无需改码；网络级硬断未测并写明 | `verify-screen-force-stop.py` 实测 |
| 2026-09-20 | cp-2 | A 项结论：不复现 + 脚本固化为回归门禁；台账登记三条脚本踩坑 | `verify-focus-three-way.py` 实测 |
