---
title: r004 设计：房内扩展能力（群聊 · 举手 · 焦点 · 屏幕共享）
description: r004 的契约面清单、数据模型与迁移、接口与函数级实现路径、Data Channel 协议、焦点×共享优先级、视觉与教学契约、回退与待实测项。
type: concept
status: draft
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
本页是 r004 的设计方案（怎么做），对应需求 `docs/00-requirements/r004-room-extras.md`（M3）。**未获「按设计做」不写代码。**
阶段 1 同批产出：总设计增量 `docs/01-architecture/r004-realtime-extras-architecture.md` + ADR-0013/0014（本批）+ ADR-0015（cp-3）。

## 1. 契约面清单（CR 定级基准物）

| 面 | 是否变 | 具体 |
| --- | --- | --- |
| 对外可见面 · 界面元素 | **变（L3）** | 抽屉拆「讨论 / 成员」双 tab；控制坞左组新增「举手」「共享屏幕」；成员行新增「给焦点」；状态条新增当前焦点与未读徽标；焦点格新增共享/焦点徽标 |
| 对外可见面 · 接口 | **变（L3，新增）** | 新增 5 组路由（`/messages`、`/hand-raise(s)`、`/focus`），不改动既有接口的请求/响应 |
| 数据模型 | **变（L3）** | 迁移 `004`：`room_hand_raises`、`room_focus` 两张新表；`chat_messages` **不改** |
| 模块边界与依赖 | 不变 | 后端 +2 服务文件 +1 路由文件；前端 +5 hooks +3 组件；**零新依赖** |
| 验收与示范动作 | **变（L3）** | 功能页演示脚本加 5 步；`smoke.py` 加 3 步（r002 的四步同批补） |
| 视觉契约 | 变 | 新增 3 个令牌与 2 处动效（含降级） |
| 回退方案 | 见 §11 | 逐 cp `revert`；两张新表保留（append-only，不删表也不影响 r003 版本运行） |

## 2. 实施顺序与文件总览

| cp | 面 | 主要文件 |
| --- | --- | --- |
| cp-2 | r003 收官回填 + smoke 补步 | `docs/...`、`backend/scripts/smoke.py` |
| cp-3 | 界面缺陷两项 | `frontend/src/App.tsx`、`styles/global.css`、`pages/RoomsPage.tsx`、`docs/03-decisions/r004-adr-0015-home-first-screen.md` |
| cp-4 | 数据层 + 后端 | `db/sql/004_r004_realtime_extras.sql`、`services/messages.py`、`services/hands.py`、`services/focus.py`、`api/routers/room_extras.py`、`services/rooms.py`（连带）、`tests/test_room_extras_api.py` |
| cp-5 | 前端实时层 | `hooks/useDataChannel.ts`、`useChatMessages.ts`、`useHandRaise.ts`、`useRoomFocus.ts`、`useScreenShare.ts`、`api/roomExtras.ts` |
| cp-6 | 前端界面 | `components/live/ChatPanel.tsx`、`MessageBubble.tsx`、`FocusBadge.tsx`、`RoomSidePanel.tsx`、`DeviceBar.tsx`、`LiveStage.tsx`、`RoomLivePage.tsx`、`styles/global.css` |
| cp-7 | 取证 + 教学页 + 收官 | `docs/tutorials/r004-room-extras.md`、`docs/rounds/r004-room-extras/{review.md,changes.md}`、README/AGENTS/roadmap/术语表 |

## 3. 数据模型与迁移（`004_r004_realtime_extras.sql`）

沿用 r002 的迁移方式（`app/db/migrate.py`：前进式文件 + 版本表；`db_init.py --reset --seed` 可重建）。

```sql
-- 举手：一次举手一行，lowered_* 为空表示「正在举手」
CREATE TABLE IF NOT EXISTS room_hand_raises (
  id             TEXT PRIMARY KEY,
  room_id        TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
  user_id        TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  raised_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  lowered_at     TIMESTAMPTZ NULL,
  lowered_by     TEXT NULL,                       -- 操作人 user_id；自己放下时 = user_id；房间结束 = 'system'
  lowered_reason TEXT NULL CHECK (lowered_reason IN ('self','other','room_ended'))
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_hand_active
  ON room_hand_raises (room_id, user_id) WHERE lowered_at IS NULL;      -- 幂等：同一人在同一房只有一条活跃
CREATE INDEX IF NOT EXISTS ix_hand_room_active
  ON room_hand_raises (room_id, raised_at) WHERE lowered_at IS NULL;    -- 快照查询

-- 焦点：事件流，一行一次设置；subject 为空表示「取消焦点」
CREATE TABLE IF NOT EXISTS room_focus (
  id              TEXT PRIMARY KEY,
  room_id         TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
  subject_user_id TEXT NULL REFERENCES users(id) ON DELETE SET NULL,
  actor_user_id   TEXT NOT NULL REFERENCES users(id),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_focus_room_time ON room_focus (room_id, created_at DESC);
```

**为什么这样设计**

- 举手表**不用布尔列**（`room_members.hand_raised`）：举手要留痕（谁在什么时候举手、被谁放下），且部分唯一索引天然解决「重复举手」的幂等；
- 焦点用**事件流**而不是 `rooms.focus_user_id` 单列：一次设置/取消都是一条可审计记录（谁改的、什么时候），当前焦点 = 最新一行的派生值，历史免费拿到；
- `chat_messages` **零改动**：发送方广播时用服务端返回的 `id` 去重，不需要 `client_msg_id`。

**结束房间连带**（`services/rooms.py:end_room`，同一个事务内）

```sql
UPDATE room_hand_raises SET lowered_at = now(), lowered_by = 'system', lowered_reason = 'room_ended'
 WHERE room_id = %s AND lowered_at IS NULL;
```

焦点无需连带（房间结束即无焦点；历史行保留）。

## 4. 接口契约（5 组，全部要求登录 + 在册成员；`ended` 房间除 GET 外一律 409 `ROOM_ENDED`）

| 方法 | 路径 | 谁能调 | 请求 | 成功响应 | 错误 |
| --- | --- | --- | --- | --- | --- |
| POST | `/api/rooms/{room_id}/messages` | 在册成员 | `{body}`（trim 后 1..500 字） | 201 `{message: MessageVO}` | 401 / 403 `NOT_MEMBER` / 400 `INVALID_INPUT` / 409 `ROOM_ENDED` |
| GET | `/api/rooms/{room_id}/messages` | 在册成员 | `?before=<id>&limit=50`（≤100） | 200 `{messages: MessageVO[]}`（DESC） | 401 / 403 / 400（limit 越界） |
| GET | `/api/rooms/{room_id}/hand-raises` | 在册成员 | — | 200 `{hands: HandVO[]}`（`raised_at` ASC） | 401 / 403 |
| POST | `/api/rooms/{room_id}/hand-raise` | 在册成员 | — | 200 `{hands: HandVO[]}`（**幂等**：已在举则原样返回） | 401 / 403 / 409 |
| DELETE | `/api/rooms/{room_id}/hand-raise` | 在册成员 | — | 200 `{hands}` | 401 / 403 / 409 |
| DELETE | `/api/rooms/{room_id}/hand-raise/{user_id}` | **Host / Moderator** | — | 200 `{hands}` | 401 / 403 `FORBIDDEN` / 400（目标没在举）/ 409 |
| GET | `/api/rooms/{room_id}/focus` | 在册成员 | — | 200 `{focus: FocusVO}` | 401 / 403 |
| POST | `/api/rooms/{room_id}/focus` | **Host / Moderator** | `{userId: string \| null}` | 200 `{focus: FocusVO}` | 401 / 403 / 400（目标不在册）/ 409 |

```ts
MessageVO = { id, roomId, userId, displayName, body, kind: 'chat'|'system', createdAt }
HandVO    = { id, userId, displayName, raisedAt }
FocusVO   = { subjectUserId: string | null, subjectName: string | null, actorUserId, setAt }
```

- 所有写接口都在**事务内先 `lock_room`**（复用 `services/rooms.py` 的既有手法）：防「房间刚被结束仍写入」的竞态；
- 权限只用既有 `assert_room_role(conn, actor, room_id, roles)`，**不新写一套判定**；
- 返回体一律返回**全量快照**（`hands` / `focus`）而不是「操作结果」：调用方拿到就能覆盖本地态，减少前后端状态不一致。

## 5. 函数级实现路径

### 5.1 后端 · `app/services/messages.py`（新）

| 函数 | 签名 | 职责 |
| --- | --- | --- |
| `list_messages` | `(conn, actor: UserVO, room_id: str, before: str \| None, limit: int = 50) -> list[MessageVO]` | 断言在册成员 → 按 `created_at < (before 对应的时间)` DESC 取 `limit` 条 → 反转为时间正序返回（前端直接渲染） |
| `post_message` | `(conn, actor: UserVO, room_id: str, body: str) -> MessageVO` | `lock_room` → 断言 `active` 且在册 → trim 校验 1..500 字 → `INSERT chat_messages(kind='chat')` → 返回带 `displayName` 的 VO |

### 5.2 后端 · `app/services/hands.py`（新）

| 函数 | 签名 | 职责 |
| --- | --- | --- |
| `list_hands` | `(conn, room_id: str) -> list[HandVO]` | 活跃举手（`lowered_at IS NULL`）按 `raised_at` ASC |
| `raise_hand` | `(conn, actor: UserVO, room_id: str) -> list[HandVO]` | 在册 + 房间 active → `INSERT ... ON CONFLICT (room_id,user_id) WHERE lowered_at IS NULL DO NOTHING`（幂等，见需求单 E3）→ 返回快照 |
| `lower_own_hand` | `(conn, actor, room_id) -> list[HandVO]` | 把 `actor` 的活跃行置 `lowered_reason='self'`（没有活跃行也返回快照，不报错——「放下」是幂等意图） |
| `lower_other_hand` | `(conn, actor, room_id, target_user_id: str) -> list[HandVO]` | `assert_room_role(host, moderator)` → 目标有活跃举手才改（否则 400）→ `lowered_by=actor.id`、`lowered_reason='other'` |
| `clear_hands_for_room_end` | `(conn, room_id: str) -> int` | 结束房间连带；返回受影响行数（进 changes.md 的证据） |

### 5.3 后端 · `app/services/focus.py`（新）

| 函数 | 签名 | 职责 |
| --- | --- | --- |
| `get_focus` | `(conn, room_id: str) -> FocusVO` | 取最新一行；无行或 `subject_user_id IS NULL` → 返回 `{subjectUserId: null, ...}` |
| `set_focus` | `(conn, actor: UserVO, room_id: str, subject_user_id: str \| None) -> FocusVO` | `assert_room_role(host, moderator)` → `lock_room` → `active` → `subject` 非空时校验其在册（`room_members.status='active'`）→ 插入新行（`null` 表示取消）→ 返回 `FocusVO` |

### 5.4 后端 · `app/api/routers/room_extras.py`（新）

8 个路由（见 §4）薄层包装：解析 → 调 service → `ok(...)`。错误一律 `AppError` + 既有稳定错误码（`NOT_MEMBER` / `FORBIDDEN` / `ROOM_ENDED` / `INVALID_INPUT`），**不发明新码**。

### 5.5 前端 · 实时层（cp-5）

| 文件 | 导出 | 职责 |
| --- | --- | --- |
| `hooks/useDataChannel.ts` | `useDataChannel<T>(room, topic, onMessage)`；`publishSnapshot(room, topic, payload): Promise<void>` | 统一订阅/发布：`TextEncoder` 编码 JSON、`reliable: true`、按 `topic` 分发；卸载时 `off(RoomEvent.DataReceived)` |
| `api/roomExtras.ts` | `roomExtrasApi.{listMessages, sendMessage, listHands, raiseHand, lowerOwnHand, lowerOtherHand, getFocus, setFocus}` | 8 个 HTTP 封装（类型与 §4 的 VO 对齐） |
| `hooks/useChatMessages.ts` | `{messages, send, sending, failed, retry, loadMore, hasMore}` | 进房拉最近 50 条 → 订阅 `lg.chat` 追加（按 `id` 去重、按 `createdAt` 排序）→ 发送走 HTTP，成功后 `publishSnapshot` 广播；失败保留本地草稿（`local-*` id）并可重发 |
| `hooks/useHandRaise.ts` | `{hands, mine, raise, lower, lowerOther}` | 订阅 `lg.hands` **全量快照**（比较 `at`，大的胜）；操作走 HTTP 并**立即用响应覆盖**本地态 |
| `hooks/useRoomFocus.ts` | `{focus, setFocus}` | 同上，订阅 `lg.focus` |
| `hooks/useScreenShare.ts` | `{ownerId, sharing, start, stop, requestStop}` | `localParticipant.setScreenShareEnabled(true/false)`；监听 `RoomEvent.TrackPublished/Unpublished` 维护 `ownerId`（`source === Track.Source.ScreenShare`）；`requestStop(userId)` 广播 `lg.screen.stop`；收到且 `targetUserId === 自己` → `stop()` |

### 5.6 前端 · 界面层（cp-6）

| 文件 | 改动 |
| --- | --- |
| `components/live/ChatPanel.tsx`（新） | 消息列表（自动滚到底；新消息 120ms 淡入，`reduced-motion` 取消）+ 输入区（Enter 发送 / Shift+Enter 换行 / 500 字计数 / 失败重发条）+ 空态「还没有人发言」 |
| `components/live/MessageBubble.tsx`（新） | 自己（右、强调色描边）/他人（左、面板色）/系统消息（居中灰字）；时间是 `HH:mm` |
| `components/live/FocusBadge.tsx`（新） | 焦点格右上角徽标：`共享 · 名称` / `焦点 · 名称`；共享时自己那颗带「停止共享」 |
| `components/live/RoomSidePanel.tsx` | 拆 **双 tab**：`讨论`（默认，ChatPanel + 申请区块）/ `成员`（活跃/非活跃 + 治理动作 + 房间码）；tab 头显示未读数 |
| `components/live/DeviceBar.tsx` | 左组加两颗：「举手 / 放下手」（举手中用强调色）、「共享屏幕 / 停止共享」；仍不绑快捷键 |
| `components/live/LiveStage.tsx` | 焦点格选择改为显式优先级函数（§7）；共享/焦点时渲染 `FocusBadge` |
| `pages/RoomLivePage.tsx` | 装配 4 个 hooks；状态条显示「焦点：名称」与未读徽标；处理 `lg.screen.stop` 的落点；抽屉默认 tab |

## 6. Data Channel 协议（房内广播）

**总原则（ADR-0013）**：**库是唯一真相**；Data Channel 只做「让另一台浏览器立刻看到」的加速层。任何「只靠广播」才能看到的状态都算设计缺陷。

| topic | 谁发 | payload | 收敛规则 |
| --- | --- | --- | --- |
| `lg.chat` | 发送消息的人（HTTP 成功后） | `{v:1, message: MessageVO}` | 按 `message.id` 去重；渲染按 `createdAt` 排序 |
| `lg.hands` | 任何改了举手状态的人 | `{v:1, at: number, hands: HandVO[]}` | **全量快照**，`at` 更大者覆盖 |
| `lg.focus` | 设置/取消焦点的人 | `{v:1, at: number, focus: FocusVO}` | 全量快照，`at` 更大者覆盖 |
| `lg.screen.stop` | 房主/协管 | `{v:1, targetUserId, requestedBy}` | 仅 `targetUserId === 自己` 时响应（调 `stop()`） |

- 进房/重连成功后**统一 `refresh()`**：`GET messages`（50 条）+ `GET hand-raises` + `GET focus` 三并发，然后才订阅通道 —— 保证「刷新/重进与库一致」（需求单 E9/E10）。
- 广播丢失的兜底：任何一次 HTTP 写操作都会返回全量快照，写的人自己覆盖本地态；读的人若恰好掉线，靠重连后的 `refresh()` 补齐。
- 消息体上限 500 字 ≈ 1.5 KB，远低于 Data Channel 单包上限（15 KB），无需分片。

### 6.1 「停他人共享」的实现选型（**待实测**）

| 方案 | 做法 | 结论 |
| --- | --- | --- |
| A · 协作停止（本轮默认） | 房主/协管广播 `lg.screen.stop{targetUserId}`；对方客户端收到后自己 `setScreenShareEnabled(false)` | 简单、零新 API；**不是强约束**（恶意/旧版本客户端可不理）——演示场景够用，文档如实写明 |
| B · 服务端强停（待实测） | LiveKit `RoomService.UpdateParticipant` 收缩该参与者的 `can_publish_sources`（去掉 ScreenShare） | 若平台真能撤销已在发布的轨道，则优先 B；**cp-6 前做一次最小实测**（改权限 → 看对方是否停止发布）并据结果定稿；若不可行保持 A 并补一句 ADR |

## 7. 焦点格优先级（ADR-0014）

| 优先级 | 条件 | 焦点格 | 徽标/提示 |
| --- | --- | --- | --- |
| 1 | 有人正在共享屏幕 | 共享画面（16:9 letterbox） | `共享 · 名称`；若是自己的共享 → 「停止共享」 |
| 2 | `focus.subjectUserId` 非空且在册 | 该成员画面 | `焦点 · 名称` |
| 3 | 有人在说话（`useActiveSpeaker`） | 说话者画面 | 声波脉冲（r002 既有） |
| 4 | 兜底 | 自己 | — |

- **共享 > 说话者**（r002 §4.8 已定）与**共享 > 手动焦点**（本轮新增判断）：共享是「请看这个材料」的强意图，且画面不能被缩小；说话不夺共享的焦点格。
- 取消共享后自动回落到 2/3/4（派生函数，不引入新状态）。
- 实现落点：`LiveStage` 的 `pickFocusTile(tracks, focus, screenShareOwner, activeSpeaker, selfId)`（纯函数，便于单测/肉眼验）。

## 8. 视觉与动效口径

| 项 | 取值 | 单点可调 |
| --- | --- | --- |
| 令牌 | `--chat-bubble-own`（自己的气泡描边，强调色 30%）、`--live-hand-active`（举手激活色 = `--accent` 的 20% 底 + 描边）、`--live-share-badge`（共享徽标底） | `global.css` `:root` |
| 消息淡入 | 120ms 位移 6px + 透明度 | `--msg-enter` |
| 举手脉冲 | 按钮一次性 2.4 秒脉冲（沿用 r002 的申请徽标手法，`prefers-reduced-motion` 静止） | 复用既有 keyframes |
| 徽标 | 焦点格右上角胶囊，与状态条同一套字体与圆角 | `.live-focus-badge` |
| 文案 | 「举手」「放下手」「给焦点」「取消焦点」「共享屏幕」「停止共享」「正在共享」；禁 emoji、禁内部词 | 功能页文案表 |
| 降级 | `prefers-reduced-motion`：消息淡入取消、脉冲静态、共享徽标不动 | 与 r002 一致 |

## 9. 教学契约（人可见的使用面）

- **场景一句话**：讨论进行中，大家能打字补充、举手要发言、由房主把发言焦点交给某人、共享屏幕讲材料 —— 而且每个人看到的是同一份现场。
- **入口**：交流页抽屉「讨论」tab（消息）/ 控制坞左组「举手」「共享屏幕」/ 抽屉成员行「给焦点」。
- **输入**：输入框回车发送（≤500 字）；点按钮举手与共享；房主/协管在成员行给焦点。
- **输出**：消息落库并双端一致（刷新不丢）；举手落库并可被房主放下；焦点两浏览器一致；共享画面进焦点格并带徽标。
- **一次典型动作（=验收示范）**：B 发「我先补充一句」→ A 端 1 秒内看到；B 举手 → A 在成员行给 B 焦点 → 两浏览器都放大 B；B 共享屏幕 → 共享画面取代焦点格，A 说话也不夺焦点。
- **开发者扩展点**：加第六个房内能力 = ① 建表（若需持久化）② 三个 service 函数（list/写/连带）③ 一组路由 ④ 一个 hook（复用 `useDataChannel`）⑤ 一个 topic ⑥ 文档四处。照 §5/§6 抄即可，无需碰主循环。

## 10. 验证矩阵（映射需求单 §5）

| 需求单条目 | 验证方式 |
| --- | --- |
| E1~E5 | `pytest backend/tests/test_room_extras_api.py`（真实 PG，conftest 回滚事务 + 打桩不使用外部调用） |
| E6 | `git grep` + 依赖文件 diff |
| E7 | `npx tsc --noEmit` / `npm run build` |
| E8~E13 | 真机双浏览器（取证报告进 `review.md`；共享与停共享需你真机配合） |
| E14 | 浏览器 `emulateMedia('prefers-reduced-motion: reduce')` + 截图 |
| E15 | 视口 720×1024 / 1258×566 截图对比（缺陷修复） |
| E16~E17 | `pytest -q` 计数 / `smoke.py` `PASS n/n` 输出 |
| E18~E20 | 审查报告 + 文档对账 |

## 11. 回退方案

- 逐 cp `revert`（append-only，禁 reset）：cp-6 回退 → 界面回到 r003（后端接口留着不影响）；cp-4 回退 → 去掉 5 组路由，两张新表**保留**（空表不影响 r003 版本运行，也不破坏 r002/r003 的既有测试）；
- 迁移不可逆部分：无（只增表、无列改写），`db_init --reset --seed` 可重建；
- 若优先级规则被推翻（ADR-0014 变更）：只需改 `pickFocusTile` 一处 + 文档，不牵动数据层。

## 12. 风险与不确定

| 项 | 说明 | 处置 |
| --- | --- | --- |
| 服务端强停共享是否可行 | §6.1 待实测 | cp-6 前实测；不可行则保持协作停止并写进文档 |
| 断网重连实测需要真机操作 | 我无法在无头浏览器里制造断网 | 需求单 E18 列为「需你配合一次（关网络 5~10 秒）」，我给最短路径 |
| 屏幕共享录制权限弹窗 | 浏览器强制用户手势 | 共享只由按钮触发；共享音频默认不勾（r002 §4.8 防呆） |
| 群聊抢专注 | 抽屉默认收起 + 不弹 toast | 若实测仍觉吵，收缩为「仅未读徽标 + 手动打开」 |
| 举手表与既有 `room_members` 语义混淆 | 举手是**瞬时状态**，不是成员身份 | 术语表新增词条，明确与 `status` 的区别 |

## 13. 覆盖矩阵落地方式

| 页面 | 何时写 | 事实源 |
| --- | --- | --- |
| 需求单 / design / 架构增量 / ADR-0013/0014 | cp-1（本批） | 本轮方案 |
| ADR-0015 + 缺陷修复说明 | cp-3 | 首页首屏口径 |
| `r004-room-extras.md`（实现页） | cp-4/5/6 随实现 | 接口/函数/并发事实 |
| `r004-room-extras-features.md`（功能页 F-18~F-22） | cp-4/5/6 随实现 | 行为/文案/按钮矩阵/演示脚本 |
| 风格指南 + 术语表 | cp-6 | 视觉与术语事实 |
| 教学页（使用者 + 开发者补节） | cp-7（跑通后写） | 实跑输出 |
| README / AGENTS / roadmap / 索引 | cp-2 与 cp-7 | 状态与命令 |

## 14. 本轮设计变更记录

| 日期 | CR | 级别 | 摘要 | 结论 |
| --- | --- | --- | --- | --- |
| （实现期追加） | | | | |
