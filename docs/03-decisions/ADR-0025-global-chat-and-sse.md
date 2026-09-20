---
title: ADR-0025 全服大屏聊天 + SSE 通知通道（HTTP 落库仍是唯一真相）
description: 公屏的存储与可见性、限流口径、SSE 只推通知型事件的协议与进程内广播的已知限制。
type: reference
status: accepted
owner: 陀梓皓
updated: 2026-09-20
---

<!-- overview -->
背景：r012 要一个「全服大屏聊天」——所有登录用户能看到与参与的公开文字流，且新建房/管理动作等通知要能实时到达浏览器。既有架构只有两套实时机制：LiveKit DataChannel（**只在房间内**，只做加速）与 HTTP 轮询（真相源）。用户 2026-09-20 的批复：Q11=2（面板放**右侧可收起的 Copilot 式侧栏**）、Q13=1（**全部消息可见**、仅当前在线者带在线点）、Q14=2（在线靠**前端 60 秒短轮询**）。本 ADR 定 SSE 通道口径；**与 ADR-0013 的关系：DataChannel 只加速、HTTP 是唯一真相的既有口径不变**，SSE 是第三个「只加速」的通道。

## 事实（实测）
1. 迁移 011 建 `global_messages`（`body` 1~500 字 CHECK + `(created_at DESC)`/`(user_id, created_at DESC)` 双索引）。
2. 用例实测：未登录可 `GET /api/global-messages` 200、`POST` 401；单条 501 字 400 / 500 字 201；窗口内第 N+1 条 429 `RATE_LIMITED` 且**不落库**；`authorOnline` 随 `users.last_seen_at` 变化。
3. SSE 帧实测：首帧 `retry: 3000`；事件帧 `id: <单调递增>` / `event: notify` / `data: {"type":…,"payload":{"id":…}}`；无事件时产出 `: ping`（间隔 = `SSE_KEEPALIVE_SECONDS`）。
4. 订阅上限实测：`SSE_MAX_SUBSCRIBERS=1` 时第二个订阅者拿到 503（不静默丢）。

## 决定
### D1 公屏是**独立一张表**，不复用 `chat_messages`
`chat_messages.room_id` 是 `NOT NULL`，公屏没有房间归属；硬塞房间 id 会让房间统计/纪要素材/级联删除全部带上公屏噪声。代价：多一张表、多两处查询（可接受）。

### D2 通道走 **SSE**（`GET /api/events`），且**事件名固定 `notify`**
理由：单向、只推通知，浏览器原生 `EventSource` 自带重连与 `Last-Event-ID`，零新依赖（不引 WS 库）。固定事件名避免前端漏解多 `event:` 名；`data` 里用 `type` 分派。

### D3 SSE **只推通知型事件**，载荷最小（只有 id 之类）
收到通知后前端照旧走 HTTP 拉真相（沿用 ADR-0013）。`publish` 同步非阻塞：队列满丢最旧并记日志，**绝不阻塞发言**。`publish` 在**落库提交之后**调用——通知丢了不影响数据正确性。

### D4 进程内广播，单进程有效（**已知限制**）
订阅者表与事件计数都在进程内存：**多进程/多机部署会漏事件**。当前演示形态（单 uvicorn 进程）不触发；要横向扩展需换 Redis pub/sub（登记为后续轮次候选）。前端靠 `EventSource` 自动重连 + 30 秒轮询兜底，功能不丢。

### D5 可见性：**未登录可看，登录才可发**（Q4=1 / Q13=1）
公屏是公开面，不加房间/成员限制；发言需要登录（401 `UNAUTHORIZED`），窗口内每人 ≤ `GLOBAL_CHAT_RATE_LIMIT` 条（默认 5 条 / 10 秒，落库计数——重启不放大额度）。

## 用户批复（2026-09-20）
- 「右侧的侧栏打开窗口，像编译器里的 coplit」（Q11=2）→ 面板形态为右侧可收起抽屉（前端在 cp-6 落地）。
- 「只 admin 可见」（Q12=2，管理后台入口；与公屏无关，记此备查）。

## 备选与否决
| 备选 | 否决理由 |
| --- | --- |
| WebSocket | 双向能力用不上；引库 + 心跳/重连/鉴权全自己写，与「HTTP 是唯一真相」并列成第二套实时机制 |
| 复用 LiveKit DataChannel 做全服广播 | DataChannel 只在房间内；全服广播要么每房间发一遍、要么建一个「大厅房间」，都与「房间=一次性讨论」的口径冲突 |
| 纯轮询（不做 SSE） | 聊天面板 30 秒才更新一次，演示观感差；且 r011 redirect-01 已批过 SSE 口径 |
| 每事件多 `event:` 名（如 `global_message` / `room_changed`） | 前端需维护多处理器；固定 `notify` + `data.type` 更不易漏 |
| 只显示当前在线用户的消息（把离线者历史消息隐藏） | 大屏会出现"消息凭空消失"，与聊天直觉冲突；改为**全部可见 + 在线点**（Q13=1） |

## 影响面
- 代码：`services/events.py`（新）、`services/global_chat.py`（新）、`repositories/global_chat.py`（新）、`api/routers/{global_chat,events}.py`（新）、`config.py`（6 项可调）、`api/errors.py`（+`RATE_LIMITED`）。
- 前端（cp-6）：`api/globalChat.ts`、`hooks/useGlobalChat.ts`、`hooks/useEventStream.ts`、`components/GlobalChatDrawer.tsx`。
- 部署：单进程限制见 D4；若上 Docker Compose 多副本需先解决广播（登记）。

### D6 `publish` 必须**线程安全**（cp-7 真机踩到后补）
同步端点（FastAPI 的 `def` 路由）在线程池里执行，订阅者的 `asyncio.Queue` 属于事件循环线程，
所以 `publish` 不能直接 `put_nowait`：订阅者正 `await queue.get()` 时，跨线程唤醒等待者会破坏事件循环
（2026-09-20 实测：进程还在、CPU 0%、8000 端口整机不再响应）。
口径：订阅时记住自己的循环，投递一律 `loop.call_soon_threadsafe(_offer, …)`。

### D7 SSE 路由**不得带任何 DB 依赖**（cp-8b 真机踩到后补）
`/api/events` 是**永不结束**的流，而 FastAPI 的依赖清理在响应结束之后才跑：只要依赖链里有一条
`db_conn`，每个订阅者就会把连接池（`max_size=8`）里的一条连接攥到流结束。
实测本机 9 条流挂上后，**所有**普通接口在 30 秒后 500（`psycopg_pool.PoolTimeout: couldn't get a connection after 30.00 sec`），
关掉流立刻恢复 200 —— 也就是说「多开几个浏览器标签页」就能把整站打死。
口径：这条流只推 `{type, payload:{id}}` 的公开通知，**未登录也允许订阅**，因此不取用户身份、不碰数据库。
守卫：`backend/tests/test_global_chat.py::test_events_route_must_not_depend_on_db`（静态查依赖树 + 运行时查池占用）
与 `smoke.py` 的「挂 9 条 SSE 时普通接口仍畅通」一步。

## 变更记录

| 日期 | 改了什么 | 依据 |
| --- | --- | --- |
| 2026-09-20 | 初版：D1~D5（独立表 / SSE + 固定 `notify` / 只推通知 / 进程内广播的已知限制 / 未登录可看登录可发）；Q11/Q12 批复记账 | 需求单 §10.1、design §4 |
| 2026-09-20 | 补 D6：`publish` 线程安全（`call_soon_threadsafe`）——真机取证时把 8000 卡死后修，附回归用例 | cp-7 实测 |
| 2026-09-20 | 补 D7：SSE 路由不得带 DB 依赖（每订阅者攥一条连接池连接 → 9 条流打满整站）——台本逐项自检时发现 46 次 500，修 + 守卫用例 + 冒烟一步 | cp-8b 实测 |
