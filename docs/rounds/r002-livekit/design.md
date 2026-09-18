---
title: r002 轮次设计入口（M2 实时房间 · 权限 · 等候室）
description: r002 的设计入口：契约面清单、教学契约、关键设计决策与轮内设计变更记录。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-18
---

<!-- overview -->
本页是 r002 的**设计入口**：说明这一轮的设计分散在哪几份文档、契约面是什么、教学契约是什么、关键决策与理由。
本页不重复内容（禁双源）：范围与验收 → `docs/00-requirements/r002-livekit-room.md`；架构增量 → `docs/01-architecture/r002-realtime-architecture.md`；模块实现 → `docs/02-modules/r002-livekit.md`；功能行为 → `docs/02-modules/r002-livekit-features.md`。
过程记录：`changes.md`（逐 cp）、`review.md`（审查）、CR 单（`cr-<序号>.md`）、重定向确认单（`redirect-<序号>.md`）。

## 1. 这一轮的设计文档在哪

| 文档 | 承担什么 |
| --- | --- |
| `docs/00-requirements/r002-livekit-room.md` | 范围、边界、本轮已定口径（Q 表）、验收清单、cp 顺序 |
| `docs/01-architecture/r002-realtime-architecture.md` | 新增拓扑、三条实时时序、配置必填、唯一出口与外部调用纪律、验证矩阵增量 |
| `docs/02-modules/r002-livekit.md` | 数据用途、业务规则、接口清单、后端函数签名、前端文件路径、边界与失败 |
| `docs/02-modules/r002-livekit-features.md` | 角色能力矩阵、功能详述、房内页布局与按钮矩阵、提示文案、双浏览器演示脚本 |
| `docs/tutorials/r002-livekit-demo.md`、`r002-livekit-dev-guide.md` | 使用者/开发者教学（**随实现跑通后写**，铁律 2） |
| `docs/03-decisions/r002-adr-0011-realtime-presence-model.md` | 长期约定（双事实源 / identity 唯一 / Token 无状态 / 外部调用时机 / 断线归因与重连 / 上限口径，9 条 + 5 条被否方案） |
| `docs/rounds/r002-livekit/redirect-01.md` | 断线重连与状态保持的确认单（confirmed-C，批复「设计进行」） |

## 2. 契约面清单（CR 定级基准物）

| 面 | 本轮契约 | 变更即 L3 |
| --- | --- | --- |
| 对外可见面 | 4 条新路由（`POST /rooms/{id}/token`、`POST /rooms/{id}/members/{uid}/kick`、`PATCH /rooms/{id}/members/{uid}`、`POST /rooms/{id}/transfer-host`）；错误码不新增；响应字段 `token/url/roomName/identity/role/ttlSeconds/expiresAt`、`livekitApplied` | 路径/字段/错误码变化 |
| 数据模型 | 不新增表与列；R-6 加一条部分唯一索引 | 表/列/索引语义变化 |
| 模块边界 | `services/livekit.py` 是 LiveKit 的唯一出口；依赖方向 `services → {repositories, security, livekit}`；外部调用在事务提交后 | 违反方向或新增第二出口 |
| 验收与示范动作 | 需求单 §4 的清单 + 功能页 §6 的 11 步演示 | 验收项或演示步骤变化 |
| 回退方案 | 单轮单分支：`git revert` 对应 cp 提交；`LIVEKIT_*` 清空后进程启动失败（不是静默降级）→ 演示前回退到 r001 形态只需 revert 本轮提交 | 回退路径失效 |

## 3. 教学契约（写什么的人能看见的面，正文随实现落地）

- **场景一句话**：几位同学围绕一个主题开一间房，获批的人进房就能开麦、开摄像头、互相同步；房主能管人（移出、任命、移交），结束后大家回到同一间房的记录页。
- **入口与命令名**：
  - 使用者：房间详情页「进入房间」→ `/rooms/:id/live`；房内底部「麦克风 / 摄像头 / 离开房间」；成员行「移出房间 / 设为协管 / 取消协管 / 移交房主」。
  - 开发者：`app/services/livekit.py` 的 5 个函数（`issue_token` / `remove_participant` / `delete_room` / `list_participant_identities` / `_run`）；前端 3 个 hooks（`useRoomToken` / `useRoomConnection` / `useLiveParticipants`）。
- **输入与输出**：输入 = 一间 `active` 房间 + 活跃成员身份；输出 = Token（`wss://` 连接凭证）+ 房内音视频 + 实时成员状态；踢人输出 = 库内 `inactive/kicked` + 对方连接被服务端断开。
- **一次典型使用动作（=验收示范）**：A 建房 → B 申请 → A 批准 → 两人进房声画互通 → A 把 B 设为协管 → 第三人进到满员被拒 → A 移出 B（B 立刻断线）→ B 再申请重进 → A 结束房间（所有人断线，房间转只读）。完整 11 步见功能页 §6。
- **开发者视角**：要换 Token 策略 → 只改 `services/livekit.py::issue_token` 与 `config.py` 的派生 TTL；要加一个新的房内能力（如 M3 的举手）→ 走 LiveKit 数据通道，落地在 `useRoomConnection` 暴露的 `Room` 实例上，不动本轮的成员/在场模型；要调试实时链路 → `list_participant_identities` 取证 + 前端 `Room` 事件日志。

## 4. 关键设计决策（为什么这么做）

| # | 决策 | 理由 | 替代方案（为何不选） |
| --- | --- | --- | --- |
| 1 | 成员身份（库）与在场（LiveKit）分属两个事实源，UI 求交 | 在场不可靠（断线残留十几秒），门禁必须落库；展示要真实 | 用在场表反写库成员：会因断网误判「离开」 |
| 2 | 上限只按成员侧判定，Token 内 `max_participants` 兜底 | 与 r001 已实现的容量校验同源；LiveKit 侧只是一道防线 | 按在场数判定：抖动时误拒 |
| 3 | 外部调用（踢人/删房）在事务提交后，失败不回滚 | 用户意图已在库内成立；失败可重试、可解释 | 事务内调用：外部超时会拖死数据库连接 |
| 4 | 断线归因**以 SDK 的 `DisconnectReason` 为准**（`PARTICIPANT_REMOVED` / `ROOM_DELETED` / `DUPLICATE_IDENTITY` 等），「再取一次 Token」降级为兜底 | SDK 直接给原因，少一次往返且更准；仍不引 Webhook | 只靠取 Token 归因：多一次请求且网络断时本就取不到（`redirect-01` C-1 修正） |
| 8 | 断线重连入 r002（连接层 + 设备层） | 自动重连是 SDK 内建能力，只是我们原来没写进设计；不写就等于把「网络抖动 5 秒」也做成「掉线」 | 全丢给 M5：演示当天网络抖一下就要重进房间 |
| 5 | 前端只用 SDK/hooks，不引 `@livekit/components-styles` | 视觉体系（ADR-0008）与默认主题冲突；交付要求禁用默认页 | 直接套组件默认样式：与现有设计割裂 |
| 6 | 演示满员用 2~3 人房 | 开 9 个浏览器不现实，而容量是同一处校验 | 真开 9 个浏览器：不可操作 |
| 7 | R-6 加「活跃 Host 唯一」索引 | transfer 靠行锁串行，索引是兜底 | 只靠行锁：一处遗漏就出现双 Host |

## 5. 前置与复用

| 项 | 状态 |
| --- | --- |
| r001 已合入 `main`（`round-r001-done`） | 已实测（`main` = `c189a87`，13 个 cp tag 齐备） |
| PostgreSQL 17.11 / 库 `learning_guide` / conda 环境 `learningguide` | 已就绪（r001 实测） |
| 后端/前端依赖（`livekit-api`、`livekit-client`、`@livekit/components-react`） | **待你批准**（需求单 §9） |
| LiveKit Cloud 项目与 `.env` 三项 | **待你操作**（需求单 §9） |
| 可复用增量 | r001 的 `rooms`/`room_members`/`join_requests` 数据层、权限判定（`assert_room_role`/`assert_manager_role`）、信封与错误码、前端外壳与设计令牌、`smoke.py` 骨架 |

## 6. 本轮设计变更记录

实现期发现设计与现实冲突时，按下表追加一行并走设计变更闸门（CR）；`design.md` 只记结论，证据放 CR 单。

| 序号 | 日期 | 级别 | 变更 | CR 单 | 落地 SHA |
| --- | --- | --- | --- | --- | --- |
| redirect-01 | 2026-09-18 | 范围变更（按 L3 看待） | 断线重连（连接层）与设备状态保持（设备层）并入 r002；业务状态恢复留 M3/M5 ①；修正断线归因（改用 SDK `DisconnectReason`）与同账号双开口径（`DUPLICATE_IDENTITY`） | `redirect-01.md`（confirmed-C） | 本次文档提交 |

## What's next

1. 你复核契约面（§2）与教学契约（§3），回「按设计做」→ 建分支 `req/r002-livekit`，从 `cp-r002-2` 开始。
2. 实现中若发现设计不成立：停手 → 取证 → 定级 → 出 CR → 等人批（铁律 7）。
