---
title: r002 实时房间实现页（LiveKit 接入 · 进房 · 踢人 · 角色）
description: r002（M2）的实时房间实现设计：LiveKit 接入模块签名、进房 Token 契约、在场口径、踢人/任命/移交/结束的实现路径、边界与验证矩阵。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-18
---

<!-- overview -->
本页是 r002（M2）的**模块实现页**：讲怎么做（数据、接口、函数路径、边界）。
功能行为、交互状态、按钮与提示文案以 **功能页** `docs/02-modules/r002-livekit-features.md` 为准；本轮范围见需求单 `docs/00-requirements/r002-livekit-room.md`；
跨模块机制（配置、连接池、会话、信封、错误码总表）见总设计 `docs/01-architecture/r001-app-architecture.md` 与 r002 增量 `docs/01-architecture/r002-realtime-architecture.md`。

## 1. 范围与里程碑归属

| 项 | 轮次 | 说明 |
| --- | --- | --- |
| LiveKit 接入（签 Token、移除参与者、删除房间、在场列表） | **r002（本文）** | 模块 `app/services/livekit.py`（§6.4） |
| 进房（获批成员取 Token 连上音视频） | **r002（本文）** | 新路由 `POST /api/rooms/{room_id}/token` + **交流页**（`/rooms/:id/live`） |
| **页面职责三分**（`redirect-04`）：房间管理页（`/rooms/:id`，口径调整）/ 交流页（专注感）/ 等待页（温暖感） | **r002（本文）** | 管理页复用 r001 页面只改口径与入口；交流页与等待页为新增页（§7） |
| 踢人 / 任命协管 / 移交房主 | **r002（本文）** | 承接 r001 期间从房间设计页剥离、存在 `docs/99-archive/` 的 M2 归档内容（2026-09-18 随 r002 移回本页并改写） |
| 邀请（限时链接 / 房间码） | 延后 | `docs/99-archive/r002-ahead-invites.md`（`status: backlog`），`invites` 表本轮不使用 |
| 群聊实时收发、举手、焦点发言、屏幕共享 | M3 | 不在本文 |
| 断线/关标签页的自动离开判定（Webhook 或定时校准） | M5 | 本文只处理「显式离开」「被踢」「房间结束」三种断开来源（§8） |
| 房间成员身份与生命周期（M1 部分） | r001 | `docs/02-modules/r001-rooms.md`；本文只写增量，冲突以本文为准并回填 r001 页「变更记录」 |

## 2. 领域模型：成员（持久）与在场（瞬时）

两条线各自有唯一事实源，**互不覆盖**：

| 概念 | 事实源 | 语义 | 谁写 |
| --- | --- | --- | --- |
| 成员 `room_members` | PostgreSQL | 授权关系：谁是这间房的 Host/协管/参与者，进入过、被移出、已离开 | 服务端（r001 已有 + 本轮 kick/role/transfer） |
| 在场 `participants` | LiveKit（Room Service / 客户端 SDK） | 此刻谁真的连着音视频；关标签页、断网即刻消失 | LiveKit（不可由我们写） |

- 进房门槛 = **成员身份**（库）；能不能连上 = **Token**（服务端签发）。在场只是展示与取证。
- 房内页把两者**求交**：以库成员列表为骨架，用 LiveKit 在场 identity 打「在线」标记（§7）。
- 「房间已满」只由成员侧判定（r001 的 `capacity` 校验）+ Token 内 `max_participants` 兜底，**不看在场数**（在场数会因断线残留十几秒而误判）。
- 应用层房间状态 `rooms.status`（`active`/`ended`）由 Host 显式结束决定；LiveKit 房间的空置超时与本状态无关（ADR-0003 已记）。
- 本节与 §8 的约定（双事实源、identity 唯一、Token 无状态、外部调用时机、断线归因与重连）已固定为 ADR：见 `docs/03-decisions/r002-adr-0011-realtime-presence-model.md`。

## 3. 数据模型（本轮增量）

**本轮不新增表、不新增迁移文件**：`001_schema.sql` 的 `rooms` / `room_members` 已具备本轮所需字段。

| 用途 | 既有结构 | 本轮新用途 |
| --- | --- | --- |
| 踢人 | `room_members.status='inactive'` + `exit_reason='kicked'` + `left_at` | `deactivate_member(..., 'kicked', now)`，无新列 |
| 任命 / 移交 | `room_members.role ∈ {host,moderator,participant}` + `rooms.host_id` | 改角色；移交时同步 `rooms.host_id` |
| 进房 | —— | Token 不落库（无状态、短 TTL；重连即重签） |
| 房间结束 | `rooms.status='ended'` + `ended_at` | 结束动作后追加「强制断开全部连接」（§6.4） |

**待你确认的唯一 schema 增量（R-6）**：加一条部分唯一索引，防并发期间出现两个活跃 Host。

```sql
-- 计划写入 backend/app/db/sql/003_r002_host_uniqueness.sql
-- 每个房间最多一个活跃 Host（transfer_host 已用 lock_room 串行化，本索引是兜底）
CREATE UNIQUE INDEX IF NOT EXISTS ux_room_members_active_host
  ON room_members (room_id) WHERE status = 'active' AND role = 'host';
```

若你不同意加，则删除本节代码块与 §10 的 R-6，并在 §8 记为已知弱点（并发双 Host：transfer 与 transfer 互斥靠行锁，理论不可达）。

## 4. 业务规则（逐操作）

| 操作 | 触发者 | 前置 | 副作用 | 错误码 |
| --- | --- | --- | --- | --- |
| 取进房 Token | 登录且**活跃成员** | 房间 `active` | 本地签发 JWT（不写库） | `UNAUTHORIZED` / `NOT_MEMBER` / `ROOM_ENDED` |
| 踢人 | Host / Moderator | 房间 `active`；目标为**活跃成员**；目标非 Host；协管不得踢协管（仅 Host 可）；不得踢自己 | `deactivate_member(target, 'kicked')`；**事务提交后**调 `remove_participant`（Cloud 带 `revoke_token_ts`） | `FORBIDDEN` / `NOT_MEMBER` / `VALIDATION` / `ROOM_ENDED` |
| 任命 / 取消协管 | **仅 Host** | 房间 `active`；目标为活跃成员且非自己；`role ∈ {moderator, participant}` | 改 `room_members.role` | `FORBIDDEN` / `NOT_MEMBER` / `VALIDATION` / `ROOM_ENDED` |
| 移交房主 | **仅 Host** | 房间 `active`；目标为活跃成员且非自己 | 目标 → `host`；原 Host → 目标原角色；`rooms.host_id = 目标` | `FORBIDDEN` / `NOT_MEMBER` / `VALIDATION` / `ROOM_ENDED` |
| 结束房间（r001 已有，本轮增量） | **仅 Host** | 房间 `active` | r001 三件事不变（`ended` / 成员 `inactive/room_ended` / 待批 `cancelled`）；**提交后**调 `delete_room` 强制断开全部连接 | `FORBIDDEN` / `ROOM_ENDED` |

规则补充：

1. **外部调用不回滚业务状态**：`remove_participant` / `delete_room` 的失败只记日志（含 `room_id`、`user_id`、异常摘要），库状态照常提交；接口照常 200（响应带 `livekitApplied` 布尔，见 §5）。
2. **被踢者可再次申请**（承接 r001 FQ-3 已定「立即允许」）；再被批准时按 r001 现状**新插一行**成员记录。
3. **Token 不缓存在库**：每次进房/重连现签；`revoke_token_ts` 与短 TTL 的差异见 §8。
4. **协管不得踢协管**：给「协管互踢」留出 Host 的最终裁决权（与 F-11 的角色定位一致）。

## 5. 接口清单（本模块增量）

| 方法 | 路径 | 谁能调 | 请求 | 响应 |
| --- | --- | --- | --- | --- |
| POST | `/api/rooms/{room_id}/token` | 活跃成员 | — | 200 `{token, url, roomName, identity, role, ttlSeconds, expiresAt}` |
| POST | `/api/rooms/{room_id}/members/{user_id}/kick` | Host/Moderator | — | 200 `{livekitApplied: bool}` |
| PATCH | `/api/rooms/{room_id}/members/{user_id}` | Host | `{role: "moderator" \| "participant"}` | 200 `MemberVO` |
| POST | `/api/rooms/{room_id}/transfer-host` | Host | `{userId}` | 200 `{members: [MemberVO], hostId}` |

- `roomName` = `room_id`（与库主键同一值，避免「LiveKit 侧名字」与库双源）；`identity` = `user_id`；`url` 来自 `LIVEKIT_URL`（**只有 URL 可以给前端**，Key/Secret 永不出后端）。
- 既有路由不变；`GET /api/rooms/{room_id}` 的响应**不加** LiveKit 在场字段（在场由前端 SDK 直接拿，避免后端多一次网络调用与双源）。

## 6. 后端实现路径（逐文件：函数签名 + 职责 + 返回）

```
backend/app/
├─ config.py                      # §6.1 增量：livekit 三项必填 + 模式校验
├─ services/livekit.py            # §6.4 新增：唯一访问 LiveKit 的模块
├─ services/rooms.py              # §6.2 增量：issue_room_token / kick_member / set_member_role / transfer_host / end_room
├─ repositories/rooms.py          # §6.3 增量：update_member_role / list_active_hosts
├─ schemas/rooms.py               # §6.6 增量：RoleIn / TransferHostIn / RoomTokenVO
├─ api/routers/rooms.py           # §6.5 增量：4 条路由
├─ db/sql/003_r002_host_uniqueness.sql  # §3 的 R-6（待你确认）
└─ tests/{test_livekit_token.py,test_rooms_members_api.py}  # §9
```

### 6.1 `app/config.py`（增量）

| 函数 | 签名 | 变化 |
| --- | --- | --- |
| `validate_startup` | `(s: Settings) -> None` | 追加：`livekit_url` / `livekit_api_key` / `livekit_api_secret` 任一为空 → `CONFIG_MISSING`（报错只报键名）；`livekit_mode ∈ {'cloud','self'}`；`room_capacity ∈ [2,8]`（既有） |

`Settings` 追加两个只读派生项：`livekit_token_ttl_seconds`（`cloud` → 3600，`self` → 300）、`livekit_timeout_seconds`（默认 10）。二者由 `livekit_mode` 推出，**不新增环境变量**，避免配置项膨胀（改口径只改这一处）。

### 6.2 `app/services/rooms.py`（既有文件，增量）

| 函数 | 签名 | 职责 / 返回 |
| --- | --- | --- |
| `issue_room_token` | `(conn: Connection, actor: UserVO, room_id: str) -> RoomTokenVO` | `assert_room_role(conn, actor, room_id, MANAGER_ROLES + ('participant',))`（即活跃成员）→ `assert_room_active` → 调 `livekit.issue_token(room_id, actor, role)` → 组装 VO |
| `kick_member` | `(conn: Connection, actor: UserVO, room_id: str, user_id: str) -> bool` | `with conn.transaction(): lock_room` → `assert_room_role(MANAGER_ROLES)` → 目标活跃且非 Host（踢自己 `VALIDATION`；协管踢协管 `FORBIDDEN`）→ `deactivate_member(..., 'kicked', now)`；**出事务后** `livekit.remove_participant(...)`，返回「外部调用是否成功」 |
| `set_member_role` | `(conn: Connection, actor: UserVO, room_id: str, user_id: str, role: str) -> MemberVO` | `lock_room` → `assert_room_role(HOST_ROLES)` → 目标活跃且非自己 → `role ∈ {'moderator','participant'}` 否则 `VALIDATION` → `update_member_role` → 返回 `MemberVO` |
| `transfer_host` | `(conn: Connection, actor: UserVO, room_id: str, user_id: str) -> list[MemberVO]` | `lock_room` → `assert_room_role(HOST_ROLES)` → 目标活跃且非自己 → 目标 `host`、原 Host 改为目标原角色、`rooms.host_id = user_id`（同一事务）→ 返回房间活跃成员列表 |
| `end_room`（改） | `(conn: Connection, actor: UserVO, room_id: str) -> RoomVO` | r001 逻辑不变；**事务提交后**追加 `livekit.delete_room(room_id)`，失败只记日志 |

### 6.3 `app/repositories/rooms.py`（增量，全部 `(conn, ...)` 首参）

| 函数 | 签名 | SQL 要点 |
| --- | --- | --- |
| `update_member_role` | `(conn: Connection, room_id: str, user_id: str, role: str) -> None` | `UPDATE room_members SET role=%s WHERE room_id=%s AND user_id=%s AND status='active'`；受影响行数 0 → service 侧已前置拦截，此处断言失败即 `INTERNAL` |
| `update_room_host` | `(conn: Connection, room_id: str, host_id: str) -> None` | `UPDATE rooms SET host_id=%s WHERE id=%s` |
| `count_active_hosts` | `(conn: Connection, room_id: str) -> int` | `SELECT count(*) FROM room_members WHERE room_id=%s AND status='active' AND role='host'`（R-6 索引断言与并发用例用） |

（踢人复用既有 `deactivate_member`、`get_active_member`、`list_members`、`lock_room`；不新增 SQL。）

### 6.4 `app/services/livekit.py`（新增；**唯一**接触 Key/Secret 与 LiveKit 网络的模块）

| 函数 | 签名 | 职责 / 返回 |
| --- | --- | --- |
| `issue_token` | `(room_name: str, user_id: str, display_name: str, role: str, ttl_seconds: int, max_participants: int) -> str` | `AccessToken(api_key, api_secret).with_identity(user_id).with_name(display_name).with_grants(VideoGrants(room_join=True, room=room_name, can_publish=True, can_subscribe=True, can_publish_data=True, room_admin=(role=='host'))).with_room_config(RoomConfiguration(max_participants=max_participants)).with_ttl(timedelta(seconds=ttl_seconds)).to_jwt()`；**纯本地签名，不联网** |
| `remove_participant` | `(room_name: str, user_id: str) -> bool` | 异步 `LiveKitAPI.room.remove_participant(RemoveParticipantRequest(room=room_name, identity=user_id, revoke_token_ts=now))`（`cloud` 模式）——**必须显式传 `revoke_token_ts`**：撤销按 token 的 `nbf` 判定，默认截止时间带 1 分钟缓冲，用默认值时被踢者在约 1 分钟内仍能拿旧票重连（官方文档原文）；`self` 模式不传该字段（自建无撤销能力，官方写法是短 TTL + 移除后不再签发）。返回是否成功，异常记日志返回 `False` |
| `delete_room` | `(room_name: str) -> bool` | `DeleteRoomRequest`：房间结束时强制断开全部连接 |
| `list_participant_identities` | `(room_name: str) -> list[str]` | `ListParticipantsRequest` → identity 列表；**供演示取证与排障用**（前端在场状态由 SDK 直接拿，不经过本函数） |
| `_run`（内部） | `(coro) -> object` | 把 `livekit-api` 的 async 调用跑在事件循环里（`asyncio.run` / 已有 loop 时 `run_until_complete`），并施加 `livekit_timeout_seconds`；**本项目后端是同步 `def` 路由**（架构页 §2），此处是唯一的 async 边界 |
| `_api`（内部） | `() -> LiveKitAPI` | 每次调用构造并按 `async with` 关闭；不缓存长连接（调用频率极低） |

要点：
- 本模块**只读 `Settings`**，不读 `process.env`，不 import repositories（依赖方向 `services → {repositories, security, livekit}`）。
- 传入的 `room_name` / `user_id` 全是库里的值，模块内部不查库、不做权限判断（权限一律在 `services/rooms.py`）。

### 6.5 路由（`app/api/routers/rooms.py` 增量）

| 路由函数 | 签名（FastAPI 依赖注入） | 行为 |
| --- | --- | --- |
| `issue_room_token` | `(room_id: str, actor: UserVO = Depends(current_user), conn: Connection = Depends(db_conn))` | 调 service → `ok(_dump(vo))` |
| `kick_member` | `(room_id: str, user_id: str, actor: UserVO = Depends(current_user), conn: Connection = Depends(db_conn))` | 调 service → `ok({"livekitApplied": applied})` |
| `patch_member` | `(room_id: str, user_id: str, payload: RoleIn, actor, conn)` | 调 service → `ok(_dump(member_vo))` |
| `transfer_host` | `(room_id: str, user_id: str = Body 内, payload: TransferHostIn, actor, conn)` | 调 service → `ok({"members": [...], "hostId": ...})` |

（路由保持薄壳：取依赖 → 调 service → 信封；事务仍在 service 内。）

### 6.6 `app/schemas/rooms.py`（增量）

| 模型 | 字段 |
| --- | --- |
| `RoomTokenVO(CamelModel)` | `token: str`、`url: str`、`room_name: str`、`identity: str`、`role: str`、`ttl_seconds: int`、`expires_at: datetime` |
| `RoleIn(CamelModel)` | `role: Literal['moderator','participant']` |
| `TransferHostIn(CamelModel)` | `user_id: str` |

（全部继承既有 `CamelModel`，出参 camelCase、库列 snake_case，与 r001 口径一致。）

## 7. 前端实现路径（React）

新增/改动文件：

| 文件 | 导出 | 职责 |
| --- | --- | --- |
| `src/api/livekit.ts` | `livekitApi.{issueToken,kickMember,setMemberRole,transferHost}` | 4 个接口调用（走既有 `http.ts`，错误直接抛服务端 message） |
| `src/hooks/useRoomToken.ts` | `useRoomToken(roomId)` | 取 Token 的 query（`staleTime: 0`、失败按错误码归因：401/403`NOT_MEMBER`/409`ROOM_ENDED`） |
| `src/hooks/useRoomConnection.ts` | `useRoomConnection(tokenInfo)` | 建 `Room` 实例、`connect(url, token)`、`disconnect()`；维护连接状态机 `connecting → connected → reconnecting → closed`；监听 `Reconnecting` / `Reconnected` / `Disconnected(reason)`（归因见 §8.4、重连见 §8.9） |
| `src/hooks/useLocalDeviceState.ts` | `useLocalDeviceState(room)` | 记麦克风/摄像头开关（React state，不落 storage）；`Reconnected` 后按记忆值重放（§8.10） |
| `src/hooks/useLiveParticipants.ts` | `useLiveParticipants(room)` | `useTracks([{source:'camera'},{source:'microphone'},{source:'screen_share'}])` → 与库成员列表按 `identity == user_id` 求交，产出 `{member, tracks, isOnline}` 列表 |
| `src/pages/RoomLivePage.tsx` | `RoomLivePage`（**交流页**） | 路由 `/rooms/:id/live`；专注布局：44px 状态条 + 舞台 + 悬浮控制条 + 管理抽屉（默认收起）；连接状态徽标（已连接 / 正在重连… / 已断开）；**未获批 → 重定向到等待页**；错误态（已结束 / 实时服务不可用 / 连接断开） |
| `src/components/live/LiveStage.tsx` | `LiveStage` | **单焦点舞台**：说话者/共享者主格 + 其余窄缩格；非焦点格降饱和 `--live-focus-dim`、亮度 −12%；焦点格上缘 2px 强调线；只有自己时居中显示空态；手动焦点/共享切换属 M3 |
| `src/components/live/ParticipantTile.tsx` | `ParticipantTile` | 单个格子：视频或（无摄像头时）姓名首字头像块、麦克风静音徽标、角色徽标、行内「移出房间 / 设为协管 / 取消协管 / 移交房主」（按角色显示） |
| `src/components/live/DeviceBar.tsx` | `DeviceBar` | 麦克风开关、摄像头开关、「离开房间」；`prejoin` 一律不做，进页面即连接 |
| `src/components/live/RoomSidePanel.tsx` | `RoomSidePanel`（管理抽屉） | 默认收起；成员列表（在线/离线分组，来自求交结果）+ 待批申请区块（复用 r001 的 `JoinRequestList`）+ 房间信息；管理动作（移出 / 设为协管 / 取消协管 / 移交房主）按角色显示 |
| `src/hooks/useChromeIdle.ts` | `useChromeIdle(seconds)` | 静默计时（指针移动 / 键盘聚焦 / 有人说话即重置），返回 `{idle}`；供交流页把状态条与控制条淡至 `--live-chrome-idle-opacity`（§8.11） |
| `src/pages/WaitingPage.tsx` | `WaitingPage`（**等待页**） | 路由 `/rooms/:id/wait`；暖色呼吸光 + 三步状态时间线 + 房间卡 + 主题简介 + 撤回/返回 + 「获批后自动进入」开关；5s 轮询 `GET /api/rooms/{id}`，获批 → 1.5s 后跳交流页（§8.12） |
| `src/components/WaitTimeline.tsx` | `WaitTimeline` | 三步时间线（已提交 / 等待房主批准 / 进入房间）：当前步暖色微亮、后续步灰；被拒或房间结束时整体转中性 |
| `src/App.tsx` | 路由 | 新增 `/rooms/:id/live`（交流页）与 `/rooms/:id/wait`（等待页）；**交流页隐藏全局侧边栏**（专注感），管理页与等待页保留 |
| `src/pages/RoomDetailPage.tsx` | 按钮（**房间管理页**口径） | 活跃成员且 `active` 时显示「进入房间」→ `/rooms/:id/live`；我有 `pending` 申请时显示「去等待页」→ `/rooms/:id/wait`；保留 r001 的申请/批准/离开/结束 |

依赖（**安装前需你批准**，见需求单 §9）：`livekit-client`、`@livekit/components-react`。

关键取舍：

1. **不引 `@livekit/components-styles`**：只用 SDK 与 hooks（`useTracks`/`VideoTrack`/`RoomAudioRenderer`），样式按 `docs/04-style/global-style.md` 自绘（暗色编辑风、Lucide 图标、零 emoji）。理由：默认主题与 ADR-0008 的视觉体系冲突，且交付要求「不得直接用 LiveKit 默认页面」。
2. **`RoomAudioRenderer` 必须挂**（组件库提供的远端音频播放器），否则别人说话听不见——这是最容易被漏掉的一步。
3. **断开归因以 SDK 的 `DisconnectReason` 为准**（§8.4），「再取一次 Token」只作兜底：不引入 Webhook、不加推送通道；网络真断时本来也取不到 Token，所以不能把它当主路径。
4. 交流页**不做轮询**：成员与在场由 SDK 事件驱动；管理抽屉里的待批申请仍用 r001 的 5s 轮询。**唯一例外是等待页**：它还没连 LiveKit，靠 5s 轮询 `GET /api/rooms/{id}` 感知「已获批」并自动进入（§8.12）。
5. **交流页零装饰**：不加载列表页的 Canvas 流场、网格质感层与《思想者》图版（ADR-0008 的装饰清单在交流页显式不适用）；底色再暗一档以贴合专注感。
6. **两页的情绪靠令牌而非新体系**：专注/温暖两组参数全部写进 `global.css` 参数区（单点可调），不引第三方动效或 UI 库。

## 8. 并发、边界与失败

| 编号 | 情形 | 处理 |
| --- | --- | --- |
| 8.1 | 8 人上限 | 三道闸：① r001 批准时应用层校验 `capacity`；② Token 内 `RoomConfiguration(max_participants=capacity)` 由 LiveKit 硬限；③ 连接失败（`max_participants` 触发）前端提示「房间已满（上限 N 人）」。**演示口径**：浏览器只有 2~3 个，用 `capacity=2~3` 的房间复现「满员被拒」，并在演示脚本里写明这是同一套校验（真实上限 8） |
| 8.2 | 踢人与被踢者「离开」竞态 | 两者都走 `lock_room`；先到者生效，后到者遇到目标 `status='inactive'` → `NOT_MEMBER`（不 500） |
| 8.3 | Cloud 不可达 | 踢人/删房失败：库照常提交，响应 `livekitApplied=false`，日志留证；**进房失败**：前端显示「实时服务暂时不可用，请稍后重试」+ 重试按钮，不影响房间详情的其他功能 |
| 8.4 | 断开来源归因（前端） | **① 先看 SDK 原因**（`Disconnected(reason)`）：`PARTICIPANT_REMOVED` → 「你已被移出房间」；`ROOM_DELETED` → 「房间已结束」；`DUPLICATE_IDENTITY` → 「同一账号已在别处进入本房间」；`CLIENT_INITIATED`（我们主动 `disconnect()`）→ 不提示；`JOIN_FAILURE` / `ROOM_CLOSED` / 无原因 → 走 ②。**② 兜底再取一次 Token**：401 → 「登录已失效，请重新登录」；403 `NOT_MEMBER` → 被移出；409 `ROOM_ENDED` → 房间已结束；网络失败 → 「连接已断开」+ 重连按钮 |
| 8.5 | 重入与 Token 复用 | 每次连接现签 Token；`cloud` 模式下踢人时**显式传 `revoke_token_ts`**，被踢者的旧 Token 立即失效（刷新也回不来，除再次获批）。`self` 模式：**LiveKit 会主动给在线客户端刷新 Token（刷新票有效期 = max(10 分钟, 原票剩余寿命)）**，所以短 TTL 只压「未刷新票」的窗口；按官方对自建的写法，靠「短 TTL（300s）+ 移除后不再签发（403 `NOT_MEMBER`）」处理，并在设计说明里如实写明这一能力边界 |
| 8.6 | 关标签页 / 断网 | 库侧**不自动置 inactive**（判定留 M5）：成员仍在名单里但显示「离线」；房主可对其「移出房间」清位 |
| 8.7 | 一人多开（同账号） | **不做真双开**：identity 用 `user_id`，同一账号在第二个窗口进入同一房间时，LiveKit 按 `DUPLICATE_IDENTITY` **把先进的那条连接踢掉**（先进窗口提示「同一账号已在别处进入本房间」）。跨房间的「在场唯一」约束仍按 r001 §9.1 不做 |
| 8.8 | 移交后原 Host 的 `room_admin` | Token 内 `room_admin` 只在签发时确定：原 Host 手里的旧 Token 仍是 `room_admin`（LiveKit 侧权限），但**应用层按钮与服务端判定立即按新角色**（库为准）。属已知取舍：真实项目可配 `UpdateParticipant` 同步权限，本项目不引入（避免更多外部调用） |
| 8.9 | **断线重连（连接层）** | 网络抖动：SDK 自动先做 ICE restart（通常无感）；需要全量重连时触发 `Reconnecting` → 房内页显示「正在重连…」且**不退出页面** → `Reconnected` 后回到「已连接」。对房内他人的表现是该成员「离开又回来」（`ParticipantDisconnected` → `ParticipantConnected`），**库侧全程不变**（不写成员状态）。只有彻底失败才走 §8.4 的闭线流程与提示 |
| 8.10 | **设备状态保持（设备层）** | 麦克风/摄像头开关记在 `useLocalDeviceState`（React state）；`Reconnected` 后按记忆值重放。**待实测（C-3）**：官方文档只写明「已发布的本地轨道会被重新发布」，未说明「已关闭（未发布）」状态的恢复行为 → cp-r002-3 实测两种情形（关摄像头后重连、静音后重连）并把结论写回本行；实测前不写结论 |
| 8.11 | **交流页专注态与降级** | 静默 `--live-chrome-idle-seconds`（默认 30）后状态条/控制条淡至 `--live-chrome-idle-opacity`（0.45）；指针移动、键盘聚焦、任何人开始说话即重置。`prefers-reduced-motion` 下取消一切位移与呼吸，只保留不透明度变化；焦点切格过渡改为瞬时 |
| 8.12 | **等待页轮询与自动进入** | 等待页 5s 轮询 `GET /api/rooms/{id}`：`pending` → 保持等待；成为活跃成员 → 暖色转强调色、文案「可以进去了」，`--wait-autoenter-delay`（1.5s）后跳交流页；`rejected`/`withdrawn` → 转中性并给「重新申请」；房间 `ended` → 提示房间已结束并回管理页。页面隐藏时暂停轮询（`document.visibilityState`），切回立刻拉一次 |

## 9. 验证矩阵（本模块）

| 层 | 命令 / 动作 | 判据 |
| --- | --- | --- |
| Token 纯函数 | `pytest backend/tests/test_livekit_token.py -q` | 解 JWT 后断言 `sub`=user_id、`name`=显示名、`video.room`=room_id、`video.roomJoin`、`roomAdmin` 仅 Host 为真、`roomConfig.max_participants`=capacity、`exp-iat`=TTL；断言 `LIVEKIT_API_SECRET` 不出现在返回值以外的任何字符串 |
| 接口层（打桩外部调用） | `pytest backend/tests/test_rooms_members_api.py -q` | 取 Token：非成员 403 `NOT_MEMBER`、已结束 409 `ROOM_ENDED`、未登录 401；踢人：协管踢协管 403、踢房主 403、踢自己 400 `VALIDATION`、踢成功 → 目标 `inactive/kicked` 且桩函数被调用一次、桩抛异常时接口仍 200 且 `livekitApplied=false`；改角色/移交：非 Host 403、成功后双方角色与 `rooms.host_id` 正确、并发用例断言活跃 Host 恒为 1（R-6 时） |
| 冒烟（真实 HTTP） | `python backend/scripts/smoke.py` | 新增步骤：成员取 Token 200 且 JWT 可解析 → 非成员取 Token 403 → 踢人后目标再取 Token 403 → 结束后取 Token 409；末尾仍 `PASS n/n` |
| 密钥检索 | `git grep -nE "API_SECRET|API_KEY" -- backend/app frontend/src` | 除 `config.py` 变量名外无命中；前端产物内无 Secret（`npm run build` 后再检索一次 `dist/`） |
| 前端类型与构建 | `cd frontend && npx tsc --noEmit && npm run build` | 无类型错误；`dist/` 产出 |
| 交流页专注态（人工） | 交流页里鼠标静止 30 秒后移动；两人以上说话 | UI 淡至 45% 且指针一移即恢复；说话者格放大、其余格降权与焦点强调线肉眼可见；页面中无装饰层（`document.querySelectorAll('canvas')` 长度 0） |
| 等待页链路（人工） | 未获批账号打开 `/rooms/:id/live` → 房主批准 | 被送到等待页（无错误卡片）；时间线当前步高亮；获批后 1.5s 自动进入交流页；撤回后再申请可复用同一页 |
| 降级（人工） | 系统开启「减少动效」后打开两页 | 无位移与呼吸，只剩不透明度变化 |
| 断线重连（人工） | 双浏览器进房后，一端断网 5~10 秒再恢复 | 自动回到房间（无需点按钮）、声画恢复、期间「正在重连…」可见；`room_members` 无新记录；关摄像头者回来仍关闭（C-3 的实测结论在此记录） |
| 人工（双浏览器，§功能页 §6） | 两个浏览器 / 一台手机扫 Cloud 链接 | 声画互通；第 N+1 人被拒并提示「房间已满」；Host 踢人后对方页面立刻断开并显示「你已被移出房间」；结束房间后所有端断开并显示「房间已结束」；被踢者再申请可获批重进 |

## 10. 分支点与待拍板

| 编号 | 事项 | 选项 | 建议 | 影响 |
| --- | --- | --- | --- | --- |
| R-2 | 邀请的落点 | ① 直接成为成员 ② 仍走等候室申请 | ②（交付要求） | 本轮不做，见 backlog 页 |
| R-6 | 是否加「活跃 Host 唯一」部分唯一索引 | 加（一条 SQL）/ 不加 | **加**（防并发双 Host，代价一条迁移） | 需你确认；不同意则删 §3 代码块 |
| R-7 | 房内是否显示「离线成员」 | 显示（灰显）/ 只显示在线 | 显示（房主需要看到谁掉了，才能清位） | 影响侧栏信息量 |
| R-8 | 被踢者的旧 Token 在 `self` 模式下的说法 | 只写「短 TTL + 拒绝再签发」/ 额外做黑名单 | 前者（ADR-0003 已定） | 影响安全叙事 |
| — | 历史角色徽标（结束后 `myRole=null`，r001 §9 遗留） | 显示 / 不显示 | 本轮**不动**（承接 r001 §9 遗留台账，等你单独拍） | 只影响只读回访观感 |

## 11. 变更记录

- 2026-09-18 建立（`status: draft`）：由 r001 的 M2 归档页移回并按 r002 重写；剥离邀请（→ `docs/99-archive/r002-ahead-invites.md`），新增进房 Token、在场口径、断开归因、前端房内页与「实时调用不回滚业务状态」等 r002 设计。
- 2026-09-18 按 `redirect-04`（批复「这项加入 r002 任务中」）：页面职责三分落地——§1 范围表、§7 文件表（新增 `WaitingPage`/`WaitTimeline`/`useChromeIdle`，交流页与管理抽屉改专注布局，新增两页路由，管理页口径与「去等待页」入口）、关键取舍新增 5/6（零装饰、情绪令牌）、§8 重排并新增 8.11/8.12、§9 加三条人工验收。
- 2026-09-18 按 `redirect-01`（批复「设计进行」）：§8.4 改为 **SDK `DisconnectReason` 优先**、取 Token 兜底；§8.7 同账号双开改为「后进踢掉先进 + 提示」；新增 §8.9 断线重连（连接层）与 §8.10 设备状态保持（设备层，含待实测项 C-3）；§7 增 `useLocalDeviceState` 与连接状态徽标；§9 加断网重连验收行。
