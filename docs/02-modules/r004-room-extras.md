---
title: r004 实现页：房内扩展能力（数据层与后端）
description: r004 的迁移 004、两张新表、三条 service、8 条路由、并发与边界、实现与设计的差异、验证矩阵（cp-4 已完成；前端部分随 cp-5/6 追加）。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
本页是 r004（M3）的**实现事实**：文件、签名、SQL、边界、验证证据。设计与口径见 `docs/rounds/r004-room-extras/design.md`；需求与验收见 `docs/00-requirements/r004-room-extras.md`。
**当前进度**：cp-2~cp-7 全部完成（数据层与后端、前端实时层、前端界面、取证与收官）。本页是实现事实源；验收逐条证据见 `docs/rounds/r004-room-extras/review.md`。

## 1. 文件与分层落点

| 层 | 文件 | 职责 |
| --- | --- | --- |
| 迁移 | `backend/app/db/sql/004_r004_realtime_extras.sql` | 建 `room_hand_raises` 与 `room_focus`（两张新表 + 3 个索引） |
| 迁移工具 | `backend/app/db/migrate.py` | ① `BUSINESS_TABLES` 加入两张新表（`table_counts`/`reset_schema` 覆盖）② `split_statements` 过滤文件内的事务控制语句（见 §6.3） |
| 仓储 | `backend/app/repositories/room_extras.py`（**新**） | 三个能力的参数化 SQL + 行映射（与 `repositories/rooms.py` 同层，只做 SQL、不开事务） |
| 服务 | `backend/app/services/messages.py`、`hands.py`、`focus.py`（**新**） | 校验 → 事务 → 快照装配 |
| 路由 | `backend/app/api/routers/room_extras.py`（**新**） | 8 条路由薄壳（`main.py` `register_routers` 注册） |
| 既有联动 | `backend/app/services/rooms.py` | `end_room` 在同一事务内追加「清空活跃举手」 |
| 模型 | `backend/app/schemas/rooms.py` | 追加 `MessageIn` / `HandVO` / `FocusVO` / `FocusIn` |
| 用例 | `backend/tests/test_room_extras_api.py`（**新**，10 个用例）、`test_schema.py`（迁移清单与计数表同步） |

> **与设计的一处分层差异**：design §5 只点名了 service 与 router，未提仓储层。SQL 按既有分层落到 `repositories/room_extras.py`（没有塞进已 400+ 行的 `repositories/rooms.py`）。对外可见面不变。

## 2. 迁移 004（数据模型）

```sql
room_hand_raises(id PK, room_id FK→rooms, user_id FK→users, raised_at, lowered_at, lowered_by, lowered_reason)
  CHECK ((lowered_at IS NULL) = (lowered_reason IS NULL))          -- 放下必须记原因，未放下必须为空
  UNIQUE (room_id, user_id) WHERE lowered_at IS NULL               -- 幂等：同一人同房只有一条活跃
  INDEX  (room_id, raised_at) WHERE lowered_at IS NULL             -- 快照查询

room_focus(id PK, room_id FK→rooms, subject_user_id FK→users NULL, actor_user_id FK→users, created_at)
  INDEX  (room_id, created_at DESC)                                -- 当前焦点 = 最新一行
```

- **举手为什么不用布尔列**：要留痕（谁何时举手、被谁放下），且部分唯一索引天然解决重复举手；
- **焦点为什么用事件流**：一次设置/取消都是一条可审计记录；当前焦点是派生值，历史免费。
- **`chat_messages` 零改动**：发送方广播用服务端返回的 `id` 去重，不需要 `client_msg_id`。
- 实测：`db_init.py` 应用后 `schema_migrations=4`、两张新表 0 行（见 §7）。

## 3. 接口契约（8 条，实测通过）

| 方法 | 路径 | 谁能调 | 成功 | 关键错误 |
| --- | --- | --- | --- | --- |
| POST | `/api/rooms/{id}/messages` | 在册成员 | 201 `{message}` | 401 / 403 `FORBIDDEN` / 400 `VALIDATION`（空或 >500 字）/ 409 `ROOM_ENDED` |
| GET | `/api/rooms/{id}/messages?before=<id>&limit=n` | 在册成员 | 200 `{messages}`（时间正序） | 401 / 403 / 409 / 400（游标不属于该房间、limit 越界） |
| GET | `/api/rooms/{id}/hand-raises` | 在册成员 | 200 `{hands}`（`raisedAt` 升序） | 401 / 403 / 409 |
| POST | `/api/rooms/{id}/hand-raise` | 在册成员 | 200 `{hands}`（幂等） | 401 / 403 / 409 |
| DELETE | `/api/rooms/{id}/hand-raise` | 在册成员 | 200 `{hands}`（幂等） | 401 / 403 / 409 |
| DELETE | `/api/rooms/{id}/hand-raise/{user_id}` | Host / Moderator | 200 `{hands}` | 401 / 403 / 400（目标没在举）/ 409 |
| GET | `/api/rooms/{id}/focus` | 在册成员 | 200 `{focus}`（无焦点时字段全空） | 401 / 403 / 409 |
| POST | `/api/rooms/{id}/focus`（`{userId \| null}`） | Host / Moderator | 200 `{focus}` | 401 / 403 / 400（目标不在册）/ 409 |

**实现与设计的差异（3 处，均为收窄或命名统一，未新增对外面）**

| # | 设计写的 | 实现为 | 原因 |
| --- | --- | --- | --- |
| 1 | 400 `INVALID_INPUT` | 400 `VALIDATION` | 不发明新错误码：`VALIDATION` 已在 r001 的错误码总表里；空串（trim 后）在 service 再挡一次 |
| 2 | 「`ended` 房间除 GET 外一律 409」 | **GET 也 409** | M3 没有归档面（M4 才做）；读取面只服务进行中的房间。M4 的归档页会按 `r003-ahead-m4-ended-rooms-archive.md` 另开只读面（§3.1 的「离开即截止」口径） |
| 3 | design §5.2 列了 5 个 hand 函数 | 第 5 个 `clear_hands_for_room_end` 折进 `rooms.end_room`（直接调 `repositories/room_extras.lower_all_hands`） | 避免 `rooms ↔ hands` 的 service 层循环 import |

## 4. 函数级（后端）

| 函数 | 签名 | 职责 |
| --- | --- | --- |
| `messages._guard_active_member` | `(conn, actor, room_id) -> None` | 统一前置：401 → 404 → 409（房间已结束）→ 403（非在册成员） |
| `messages.list_messages` | `(conn, actor, room_id, before: str\|None, limit=50) -> list[MessageVO]` | 解析游标（id → 时间）→ 倒序取 limit 条 → **反转为时间正序**返回 |
| `messages.post_message` | `(conn, actor, room_id, body) -> MessageVO` | 事务内 `lock_room` → 校验 → `INSERT chat_messages` → 取回 `created_at` |
| `hands.list_hands` / `raise_hand` / `lower_own_hand` / `lower_other_hand` | 见 `services/hands.py` | 快照式返回（全量 `hands`），写操作都在事务内 `lock_room`；`lower_other_hand` 断言 Host/Moderator 且目标必须有活跃举手 |
| `focus.get_focus` / `set_focus` | 见 `services/focus.py` | 当前焦点 = 最新事件行；`set_focus` 只允许 Host/Moderator，目标必须是在册成员 |
| `rooms.end_room`（改动） | `(conn, actor, room_id) -> RoomVO` | 追加 `lower_all_hands`（与「房间置 ended / 成员转 inactive / 待申请转 cancelled」同事务） |

## 5. 并发与边界（实现要点）

1. **所有写操作先 `lock_room`**（复用 r001 的房间行锁），因此「刚被结束仍写入」不会出现：结束请求持有行锁 → 写请求排队 → 拿到锁时 `assert_room_active` 抛 409。
2. **举手幂等靠库**：`INSERT … ON CONFLICT (room_id, user_id) WHERE lowered_at IS NULL DO NOTHING`；并发双请求只会有一条活跃行（用例 `test_hand_raise_is_idempotent_and_lowerable` 覆盖串行幂等，库级由部分唯一索引兜底）。
3. **焦点是事件流**：只插不改，因此并发下不会互相覆盖（最后写入者成为当前焦点，`ORDER BY created_at DESC, id DESC` 定序）。
4. **结束房间连带**：`end_room` 事务内同时改房间、成员、申请、举手四处；用例 `test_end_room_clears_active_hands` 断言 `lowered_reason='room_ended'`。
5. **广播不在后端**：服务端只落库与返回快照；房内加速由前端 `useDataChannel` 负责（ADR-0013）。

## 6. 迁移工具的修复（本轮暴露的 r002 遗留问题）

### 6.1 现象
`db_init.py` 在 r004 的 004 迁移落地时报 `InvalidSavepointSpecification: 保存点"_pg3_1"不存在`，迁移中止。

### 6.2 根因
`003_r002_host_uniqueness.sql` 文件里写了 `BEGIN;` / `COMMIT;`，而 `run_migrations` 已经用 `with conn.transaction()`（savepoint）包住整批语句 —— 内层 `COMMIT` 把外层事务一起提交掉，随后 psycopg 释放 savepoint 失败。后果很隐蔽：**索引建好了、版本行没写**，此后每次迁移都在同一处失败（`schema_migrations` 停在 001/002）。

### 6.3 修法
`split_statements` 过滤掉迁移文件里的事务控制语句（`BEGIN` / `COMMIT` / `ROLLBACK` / `START TRANSACTION` / `END`），事务边界统一由 `run_migrations` 负责；**不改历史迁移文件**（保留兼容）。实测修复后 `db_init` 输出：`本次应用版本：003_r002_host_uniqueness, 004_r004_realtime_extras`、`schema_migrations=4`。

## 7. 验证矩阵（对应需求单 §5 的 E1~E6）

| 条目 | 证据 | 结论 |
| --- | --- | --- |
| E1 发消息：在册成员 201 / 非成员 403 / 未登录 401 / 空或超长 400 / ended 409 | 用例 `test_post_message_requires_login_and_membership`、`test_post_message_validation`、`test_post_message_after_end_conflicts`；活服务探针实测 201（body 被 trim）与 409 `ROOM_ENDED` | 通过 |
| E2 拉消息：时间正序 + `before` 分页 + 越界 400 | 用例 `test_post_and_list_messages`、`test_pagination_with_before`；探针实测 200 | 通过 |
| E3 举手三态：幂等 / 自己放下 / 他人放下（记 `lowered_by`）/ 非管理者 403 / 目标没举 400 | 用例 `test_hand_raise_is_idempotent_and_lowerable`、`test_lower_other_hand_requires_manager`；探针实测「房主放下他人 → 快照变空」 | 通过 |
| E4 焦点：设置/取消/权限/目标在册 | 用例 `test_focus_set_clear_and_permissions`；探针实测 `subjectName=cp4成员`、取消后 `null` | 通过 |
| E5 结束房间连带：活跃举手全部置 `room_ended` | 用例 `test_end_room_clears_active_hands` | 通过 |
| E6 零新增依赖 / 密钥不入库 | 依赖文件未改（无新包）；新增文件内无凭据 | 通过 |

**回归**：`pytest backend/tests -q` → **105 passed**（r003 基线 95 + 新增 10）；`smoke.py` → **PASS 29/29**；`db_init.py` → `schema_migrations=4`、`room_hand_raises/room_focus` 建表成功。

## 9. 前端实时层（cp-5）

### 9.1 文件

| 文件 | 导出 | 职责 |
| --- | --- | --- |
| `src/api/roomExtras.ts`（新） | `roomExtrasApi`（8 个方法）、`Hand` / `Focus` 类型、`MESSAGE_LIMIT` | HTTP 封装（唯一真相在库，ADR-0013） |
| `src/hooks/useDataChannel.ts`（新） | `CHANNEL_TOPIC`、`publishSnapshot`、`useDataChannel<T>` | 统一订阅/发布：JSON 编码、`reliable: true`、按 topic 分发、卸载时 `off` |
| `src/hooks/useChatMessages.ts`（新） | `useChatMessages(room, roomId, enabled)` | 进房/重连拉库 + 发送落库 + 广播去重合并 + 分页 `loadMore` + 失败可重发 |
| `src/hooks/useHandRaise.ts`（新） | `useHandRaise(room, roomId, enabled, myUserId)` | 快照收敛（`at` 大者胜）+ raise/lower/lowerOther |
| `src/hooks/useRoomFocus.ts`（新） | `useRoomFocus(room, roomId, enabled)` | 同上（焦点是服务端同步的唯一焦点） |
| `src/hooks/useScreenShare.ts`（新） | `useScreenShare(room, status)` | 开/停共享、`ownerId` 派生、协作式停止请求 |
| `src/hooks/useRoomConnection.ts`（改动） | —— | **dev-only** `window.__lgRoom`（U15）：事件注入与排障入口，生产构建不含（已实测） |

### 9.2 协议与收敛（实现即契约）

| topic | 载荷 | 收敛规则 |
| --- | --- | --- |
| `lg.chat` | `{v:1, message}` | 按服务端 `id` 去重、按 `createdAt` 升序 |
| `lg.hands` | `{v:1, at, hands[]}` | 全量快照，`at` 大者覆盖 |
| `lg.focus` | `{v:1, at, focus}` | 全量快照，`at` 大者覆盖 |
| `lg.screen.stop` | `{v:1, targetUserId, requestedBy}` | 只有 `targetUserId === 自己` 时响应并停止共享 |

- **`refresh()` 是"与库一致"的保证**：三个状态 hook 都在 `enabled`（连接成功）时拉一次库，再订阅通道；重连成功后同样会触发。
- **发送路径**：HTTP 落库成功 → 用服务端返回的 VO 覆盖本地 → 广播同一份 VO（广播失败只 `console.warn`，不影响落库）。
- **失败可重发**：发送失败的消息进入 `pending`（标 `failed`），`retry(pendingId)` 重发；不吞用户输入。

### 9.3 证据

- `npx tsc --noEmit` exit 0；`npm run build` exit 0（1978 模块；产物 CSS 29.89 kB / JS 903.25 kB）。
- `dist/assets/*.js` 内 `__lgRoom` 出现次数 = **0**（U15「生产构建不含」实测通过）。
- **双浏览器真机（两个真实浏览器上下文，同一个 LiveKit 房间 `room_6026ed81aee50a24`）**：两端 `__lgRoom.state === 'connected'`；A 在 `lg.chat` 发布 `{v:1,message:{id:'probe-1'}}` → **B 收到**（`topic=lg.chat`、`from=usr_demo_host`、正文逐字一致）；B 反向发布 → **A 收到**；同源 HTTP `POST /messages` → 201、`GET /messages` → 200 且能回读。
- **限制（如实）**：`lg.hands` / `lg.focus` / `lg.screen.stop` 三条 topic 只做了载荷形状与代码路径检查，双端实测随 cp-6 的界面一起做（那时才有按钮可点）。

## 10. 前端界面（cp-6）

### 10.1 文件与落点

| 文件 | 变化 | 关键点 |
| --- | --- | --- |
| `components/live/stageLayout.ts`（新） | 纯函数 | **全仓唯一**决定「谁被放大、缩格怎么排、框多大」的地方：焦点优先级（ADR-0014）+ 尺寸阶梯（k≤3 单列 / 4~6 双列 / 7 三列 / 竖屏或挤不下→底部横条）+ `metrics` |
| `components/live/LiveStage.tsx` | 重写 | 只渲染 `computeStageLayout` 的结果；缩格条 4 种模式类名；焦点/共享徽标；「在册但离线」的焦点用头像占位；自带「停止共享」（自己的共享） |
| `components/live/FocusBadge.tsx`（新） | 徽标 | `.chip-focus`（Crosshair）/ `.chip-share`（MonitorUp）；只标注**人为**状态，说话者不标注 |
| `components/live/ParticipantTile.tsx` | 扩展 | 新增 `badge` 与 `displayNameOverride` |
| `components/live/ChatPanel.tsx` + `MessageBubble.tsx`（新） | 讨论区 | Enter 发送 / Shift+Enter 换行 / 500 字计数 / 失败重发 / 更早消息分页 / 时间只在间隔 > 5 分钟时显示 |
| `components/live/RoomSidePanel.tsx` | 双 tab | 「讨论」（默认：举手条 + ChatPanel）与「成员」（原治理内容）；成员行新增「给焦点 / 取消焦点」「请求停止共享」 |
| `components/live/DeviceBar.tsx` | 两颗新按钮 | 「举手 / 放下手」（高亮 + 一次性脉冲）、「共享屏幕 / 停止共享」 |
| `pages/RoomLivePage.tsx` | 装配 | 4 个 hook 接线；状态条「共享 名称 / 焦点 名称 / 焦点已失效」；抽屉按钮未读徽标（`9+` 封顶）；停止共享提示 |
| `styles/global.css` | 令牌与样式 | §8.9 令牌全表落库；`.chip-focus`/`.chip-share`；缩格固定 176×99 + 四种模式；聊天与举手样式；`prefers-reduced-motion` 扩展 |

### 10.2 实现在意过的两件事

1. **上缘线不能用 box-shadow 做动画**：先写的 `@keyframes` 直接动 `box-shadow`，而动画的填充值优先级高于静态声明 → 共享格的 3px 永远不生效（实测只测到 2px）。改为用 `::before` 画线（2px，共享 3px），动画只做 `scaleX + opacity`。实测：共享格 `::before` 高度 = **3px**、颜色 `rgb(124,240,196)`。
2. **ChatPanel 的副作用只依赖长度**：`onChanged` 每次都换引用，若进依赖数组会每次渲染都跑；实现里只依赖 `rows.length`，并由父组件传稳定回调。

### 10.3 证据（对应需求单 §5 的 E8~E14）

双浏览器真机（Playwright 两个上下文 + 三个额外成员上下文，同一房间；截图在 `%TEMP%\lg_cp6\`）：

| 条目 | 实测 |
| --- | --- |
| E8 群聊双端 | A 点发送 → A 列表出现该条；B 端 1 秒内收到同一条（另跑一次诊断：A/B 两端正文数组逐字相同，含 UI 发送与裸通道两种路径） |
| E9 刷新与库一致 | 库 `GET /messages` 3 条 vs 刷新后页面 3 条，**内容数组完全相同** |
| E10 举手双端 | B 点「举手」→ B 按钮变「放下手」；A 端出现「正在举手：王一诺」+「放下 王一诺」；A 放下 → 两端回到未举手 |
| E11 焦点双端 | A 给 B 焦点 → A 端徽标「焦点 · 王一诺」、B 端「焦点 · 你」、A 状态条「焦点 王一诺」；取消后徽标消失 |
| E12 共享与优先级 | B 共享 → A 端徽标「共享 · 王一诺」、状态条「共享 王一诺」、共享格上缘线 3px；**「共享中说话不夺焦点」未单独实测**（测试环境无人出声，且该断言由 `computeStageLayout` 的优先级决定，属 cp-7 可补的人工项） |
| E13 停他人共享 | A（房主）点「请求停止共享」→ B 端按钮回到「共享屏幕」、A 端共享徽标数 0、B 端提示「房主请求你停止共享屏幕（已为你停止）」 |
| E14 布局动力学 | 5 人在线（焦点外 4 格）→ rail 类名 `live-rail-double`、缩格 4 个且**每个都是 176×99**、焦点格 1016×572；竖屏/满员的横条模式由 `railMode='strip'` 决定（数字量测见 cp-7） |
| E14b reduced-motion | `emulate_media(reduced_motion=reduce)` 后焦点格 `::before` 与聊天气泡 `animation-name = none` |

### 10.4 顺带修的一个操作面问题

`RoomLivePage` 的抽屉按钮文案由「成员与管理」改为「**讨论与成员**」（现在它是两个 tab 的入口），`aria-label`/`title` 同步带上未读数与门口等待数。

## 11. 收官取证与遗留（cp-7）

### 11.1 本轮最终门禁数字

| 门禁 | 结果 |
| --- | --- |
| `pytest backend/tests -q` | **105 passed**（r003 基线 95 + r004 新增 10） |
| `smoke.py --base-url http://127.0.0.1:8000` | **PASS 36/36**（r002 四步 + r004 三步已并入） |
| `npx tsc --noEmit` / `npm run build` | exit 0 / exit 0（1988 模块） |
| `db_init.py` | 应用 `003`+`004`；`schema_migrations=4` |
| 双浏览器真机 | 群聊 / 举手 / 焦点 / 共享 / 协作式停共享 / 刷新一致 / 布局阶梯 / 窄屏竖屏 / 降级 全绿（详见 review.md） |

### 11.2 布局量测（抽屉关闭）

| 视口 / 人数 | rail 模式 | 缩格 | 焦点格 | 溢出 |
| --- | --- | --- | --- | --- |
| 1440×900，2 人 | single | 1 格 176×99 | 1156×650 | 0 |
| 1440×900，4 人 | single | 3 格 176×99 | 1156×650 | 0 |
| 1440×900，6 人 | double | 5 格 176×99（2 列） | 1016×572 | 0 |
| 1440×900，8 人 | triple | 7 格 176×99（3 列） | 828×466 | 0 |
| 1258×566，8 人 | triple | 7 格 176×99 | 562 | 0 |
| 720×1024，8 人 | strip | 672×321（3 行） | 672×378 | 0 |
| 900×600，8 人 | strip | 852×210（2 行） | 622×350 | 0 |

### 11.3 遗留（如实，不藏）

1. **E18b（本地 `livekit-server` 停机 8 秒）未做**：本轮两种自动化真断手段不成立（Playwright `set_offline` 在窗口内不触发 SDK 重连态；本地服务器未搭）。
2. **E18c（物理断网 8 秒 + 设备保持）待用户演练**：载体 `reconnect-drill.bat` 已进仓库根；四项观察回填 review.md 后本条闭合。
3. **「共享中说话不夺焦点」**：未单独实测（测试环境无人出声）；由 `computeStageLayout` 的优先级保证，建议真机点一次。
4. ~~**服务端强停共享**~~ **已闭合（r013 cp-3，2026-09-20）**：可复跑脚本 `frontend/scripts/verify-screen-force-stop.py` 真机取证——A 端共享中**不点「停止共享」**、直接关掉标签（等价 MV-2 的「杀标签」），B 端 **0.5 秒**自动清格并恢复宫格（两次实测同值）；手段为 WS 正常关闭，**网络级硬断**未测（需防火墙/物理断网，见 r013 需求单 §10.5）。实现侧无需改动：`useScreenShare` 已订阅 `TrackUnpublished` / `ParticipantDisconnected` → `scan()` 重算共享者。
5. **窄屏 + 抽屉同开**：抽屉占 360px，会把舞台压到 300px 级（缩格挤成一列、焦点格约 280px）。这是「抽屉优先」的取舍，不是布局 bug；若后续要改属 M5 候选。

## 12. r012 补丁：系统消息的补广播（cp-8c）

**现象**（r012 台本逐项自检时发现，真机、页面 visible + focused）：房主批准入房 / 有人凭邀请码加入 / 移出成员后，
系统消息**已经写库**（`GET /api/rooms/{id}/messages` 查得到），但房主讨论抽屉 **20 秒不出现**；
切 tab、关开抽屉都无效，**只有整页刷新（F5）才出现**。

**根因**：`useChatMessages` 只在 `enabled`（进房/重连）时拉库，之后靠 DataChannel 增量合并 ——
而广播由**发送方客户端**在自己发消息时发出；系统消息是**服务端**写的，没有任何客户端广播它，也不在轮询范围内。
成员列表/人数不受影响（那条走 3 秒轮询与名册广播），所以只有「讨论流里的系统消息」这一处哑掉。

**修法**（前端两处，不动协议、不动后端）：
1. `useChatMessages.refresh()`：拉到「近 30 秒内新出现、且本端没入列过的」`kind === 'system'` 消息时，
   复用既有 `CHANNEL_TOPIC.chat` 补广播一条 `{ v: 1, message }`；收到方照旧按 id 去重合并，
   已知 id 不再广播（不自激），30 秒窗口同时避免把历史系统消息重播一遍。
2. `RoomLivePage.refreshRoster()`：治理动作（批准 / 移出 / 离开 / 结束）成功后连带 `chat.refresh()`，
   让**执行者**这一端也立刻把新系统消息播出去（被批准者的客户端进房首次拉取时同样会播，两条路互为兜底）。

**证据**：`frontend/scripts/verify-runbook-flow.py`（真浏览器跑台本 S2→S8 + 大屏）由 **16/18 → PASS 18/18**，
其中 S3「批准后房主端出现『XX 加入了房间』」、S7「房主端出现『XX 通过邀请链接加入』」两条由 FAIL 转 OK。

## 8. 变更记录

| 日期 | 轮次 | 变更 | 依据 |
| --- | --- | --- | --- |
| 2026-09-20 | r012 `cp-8c` | 追加 §12：系统消息补广播（房内讨论流此前只有 F5 才看得到系统消息）；前端两处小改 + 台本行为流脚本 18/18 | r012 台本逐项自检；`verify-runbook-flow.py` |
| 2026-09-19 | r004 `cp-7` | 追加 §11 收官取证与遗留：最终门禁数字、7 档布局量测表、5 条遗留（含 E18b 未做、E18c 待演练） | 用户「做」；review.md 定稿 |
| 2026-09-19 | r004 `cp-6` | 追加 §10 前端界面：`stageLayout` 纯函数 + 四级 rail + 徽标 + 讨论区 + 双 tab + 控制坞两颗新按钮 + 令牌落库；记录两处实现坑与 E8~E14 双浏览器证据 | design §5.6、§7、§8；需求单 §5 |
| 2026-09-19 | r004 `cp-5` | 追加 §9 前端实时层：5 个 hook + `roomExtras` API + dev-only 调试句柄；记录协议收敛规则与双浏览器真机证据 | design §5.5、§6；需求单 E7 |
| 2026-09-19 | r004 `cp-4` | 建页：迁移 004 + 仓储 + 三条 service + 8 条路由 + 结束房间连带 + 10 个用例；记录 3 处实现差异与迁移工具修复 | design §3~§5、需求单 §5 E1~E6 |
