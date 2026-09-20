---
title: r013 审查与验收对账
description: 演示就绪五项的验收逐条对账（E1~E12）、规则核对、真机证据、未闭合项与合并指引。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-20
rounds: [r013]
---

<!-- overview -->
事实源：`docs/00-requirements/r013-demo-readiness.md`（验收 E1~E12）、`docs/rounds/r013-demo-readiness/design.md`。本页在 cp-7 定稿。

## 1. 验收逐条对账（E1~E12）

| # | 条目 | 实现位置 | 证据 | 结论 |
| --- | --- | --- | --- | --- |
| E1 | 三人档焦点三端一致 | `frontend/scripts/verify-focus-three-way.py`（三隔离 Chrome） | **PASS 8/8 ×3 次**（2026-09-20 实测）：三端 `data-stage-mode=focus`、`.is-focus` 各 1、焦点 identity 三端同为 `usr_012cc…`；另有 1 次定向复跑（举手→房主端举手格 **2.0 秒**出现、服务端 hands 1 条、第三端同步） | **通过（原现象不复现）** |
| E2 | 焦点不受名册/时序影响 | 同上（三人刚进房即给焦点，未等名册刷新） | 三次运行均在进房后 6 秒内给焦点，三端一致 | **通过** |
| E3 | 强停共享清格 | `frontend/scripts/verify-screen-force-stop.py`；实现侧沿用 `useScreenShare.scan()` | 两次真机：A 共享 → B 端共享格出现 → 关 A 标签 → B 端 **0.5 秒**清格、宫格恢复 1 格（截图 `%TEMP%\lg_sharestop_shots\`） | **通过** |
| E4 | 强停边界如实 | 同上 | 脚本结论行写明：手段=WS 正常关闭（非网络级硬断，硬断见 §10.5 断线方案，本轮未测）；「画面冻结」在无头静态源下**判定不了**，故不作结论 | **通过（如实）** |
| E5 | worker 连接重试 | `backend/agents/retry.py::retry_async` + `transcriber._connect_with_retry` | 用例 5 条（`test_connect_retry.py`）：三次失败后成功（退避 `[2.0, 4.0]`）、全失败抛**最后一次**异常且 `on_error` 收到 1/2/3、退避复用末值、`CancelledError` 不重试、`attempts<1` 报错 | **通过** |
| E6 | worker 错误可见 | `SttHeartbeatIn.last_error` → `stt_service.record_heartbeat` → `/rooms/{id}/stt-status.lastError` → 芯片 `title` | 用例 1 条（带 `lastError` 的心跳读得回、不带则清除）；**真机**：假心跳造错 → 芯片 title = 「…；最后错误：连接失败（3 次）：APIConnectionError: timed out waiting for ReadyForRoomEventRequest」，清掉后 title 不含该段 | **通过** |
| 待填 | E7~E12 | | | 见对应 cp |

## 6. 未闭合清单（交你复核）

（cp-7 填）

## 8. 变更记录

| 日期 | 版本 | 改了什么 | 依据 |
| --- | --- | --- | --- |
| 2026-09-20 | cp-4 | E5/E6 对账：worker 连接重试（纯函数 + 5 用例）与错误透出（用例 + 真机芯片 title）；后端按 PID 重启加载新代码 | `test_connect_retry.py`、`test_stt_heartbeat.py`、真机 |
| 2026-09-20 | cp-3 | E3/E4 对账：强停共享 0.5 秒清格；边界（非网络级硬断、冻结判定不了）如实写明 | `verify-screen-force-stop.py` 实测 |
| 2026-09-20 | cp-2 | E1/E2 对账：三人档焦点**不复现**，脚本三次全绿；登记脚本三条踩坑 | `verify-focus-three-way.py` 实测 |
| 2026-09-20 | 骨架（cp-1） | 建页 | 需求单 §8 |
