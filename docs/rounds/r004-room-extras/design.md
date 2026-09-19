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

## 0. 本页怎么读（导航与单一事实源）

**这一页只讲「怎么做」**：契约面、数据模型、接口、函数、协议、结构、样式、验证、回退。需求与验收在 `docs/00-requirements/r004-room-extras.md`；方向在 `docs/00-project/global-roadmap.md` §3 的 M3 行。

| 你想找什么 | 去哪一节 |
| --- | --- |
| 这轮动了哪些对外的面（CR 定级基准） | §1 |
| 建了什么表、结束房间的连带怎么做 | §3 |
| 有哪几个接口、错误码是什么 | §4 |
| 某个函数签名 / 某个文件改什么 | §5 |
| 广播协议（topic、payload、收敛） | §6 |
| 谁被放大、缩格怎么排、人数变了框怎么变 | §7 |
| 颜色 / 徽标 / 动效 / 令牌（单点可调） | §8 |
| 验收怎么取证、断线怎么测 | §10 |

**单一事实源（避免各页各写一套）**

| 事实 | 唯一出处 | 其他页只许引用 |
| --- | --- | --- |
| cp 的定义与完成判据 | 需求单 §8 | 本页 §2 只列「每个阶段碰哪些文件」 |
| 验收条目（E1~E23） | 需求单 §5 | 本页 §10 只做「E → 验证方式」的映射 |
| 界面与交互口径（U1~U16） | 需求单 §4 | 本页 §8 展开成可实现的规格 |
| 设计令牌（含默认值） | 本页 §8.9 | 风格指南 §12.1 在 cp-6 落库时照抄，不另拟 |
| 焦点优先级 | 本页 §7.1（ADR-0014） | 组件内不再写判断，统一调 `computeStageLayout` |
| Data Channel 协议 | 本页 §6 | 开发者教学在 cp-7 引用 |

**术语**：`k` = 在线的非焦点人数（最多 7）；**rail** = 右侧（或底部）的缩格条；**焦点格** = 被放大的那一块；**快照** = 一次返回全量状态的响应/广播；**一场讨论** = 一个房间从开始到结束（ADR-0012）。

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

> cp 的定义与完成判据只在本轮需求单 §8 维护；下表只回答「每个阶段碰哪些文件」。

| 阶段 | 面 | 主要文件 |
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
| `components/live/LiveStage.tsx` | 焦点格与缩格全部由 `computeStageLayout`（§7.6）派生（**组件里不再写优先级判断**）；共享/焦点时渲染 `FocusBadge` |
| `pages/RoomLivePage.tsx` | 装配 4 个 hooks；状态条显示「焦点：名称」与未读徽标；处理 `lg.screen.stop` 的落点；抽屉默认 tab |

## 6. Data Channel 协议（房内广播）

### 6.1 总则与 topic 表

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

### 6.2 「停他人共享」的实现选型（**待实测**）

| 方案 | 做法 | 结论 |
| --- | --- | --- |
| A · 协作停止（本轮默认） | 房主/协管广播 `lg.screen.stop{targetUserId}`；对方客户端收到后自己 `setScreenShareEnabled(false)` | 简单、零新 API；**不是强约束**（恶意/旧版本客户端可不理）——演示场景够用，文档如实写明 |
| B · 服务端强停（待实测） | LiveKit `RoomService.UpdateParticipant` 收缩该参与者的 `can_publish_sources`（去掉 ScreenShare） | 若平台真能撤销已在发布的轨道，则优先 B；**cp-6 前做一次最小实测**（改权限 → 看对方是否停止发布）并据结果定稿；若不可行保持 A 并补一句 ADR |

## 7. 舞台结构与布局动力学

### 7.1 焦点优先级（ADR-0014）

| 优先级 | 条件 | 焦点格 | 徽标/提示 |
| --- | --- | --- | --- |
| 1 | 有人正在共享屏幕 | 共享画面（16:9 letterbox） | `共享 · 名称`；若是自己的共享 → 「停止共享」 |
| 2 | `focus.subjectUserId` 非空且在册 | 该成员画面 | `焦点 · 名称` |
| 3 | 有人在说话（`useActiveSpeaker`） | 说话者画面 | 声波脉冲（r002 既有） |
| 4 | 兜底 | 自己 | — |

- **共享 > 说话者**（r002 §4.8 已定）与**共享 > 手动焦点**（本轮新增判断）：共享是「请看这个材料」的强意图，且画面不能被缩小；说话不夺共享的焦点格。
- 取消共享后自动回落到 2/3/4（派生函数，不引入新状态）。
- 实现落点：`computeStageLayout`（§7.7）—— 优先级只在这里判一次，`LiveStage` 只渲染结果。

### 7.2 尺寸变换总则

**本节回答一件事**：在**同一场讨论里**（我们的房间 = 一场讨论，ADR-0012），人数从 1 涨到 8、有人进出、有共享、焦点易手时，每块框的大小怎么变、什么时候变、变多少、动画多长 —— 且**观众永远不会被「框突然变小」吓到**。

### 7.3 四条防意外原则

1. **缩格尺寸固定，数量与列数变化**：单个缩格恒为 `176 × 99`（16:9）。一个人加入**不会**让别人的格子变小 —— 这是最容易踩的坑（「均分高度」算法就会这样，现状 `height: calc((100% - 2*gap)/3)` 正是均分）。
2. **焦点格只在两个门槛上变尺寸**：`k = 4`（rail 单列 → 双列）与 `k = 7`（双列 → 三列或横条）；其余时刻焦点格尺寸**不变**。
3. **焦点易手是唯一「大变小 / 小变大」的事件**，且两侧**同帧同步过渡**（240ms），不做跨容器位移（FLIP 会把画面糊掉）。
4. **共享不改变任何尺寸**：共享与被共享者用的是**同一个 16:9 焦点格**，只换内容（240ms 交叉淡入），rail 一动不动。

### 7.4 尺寸阶梯（`k` = 在线的非焦点人数 = 在线人数 − 1，最多 7）

| `k` | rail 形态 | rail 总宽 | 缩格 | 焦点格宽 | 出现场景 |
| --- | --- | --- | --- | --- | --- |
| 0 | 无 rail | 0 | — | `min(可用宽, 16/9 × 可用高)`，居中 | 一个人（自己） |
| 1–3 | **单列**（默认） | 176px | 176 × 99 恒定 | 同上（减去 rail 与 gap） | 2~4 人 |
| 4–6 | **双列**（每列最多 3） | `2×176 + 12 = 364px` | 176 × 99 恒定 | 缩小一档 | 5~7 人 |
| 7 | **三列**（若焦点格仍 ≥ `--focus-min-width: 480px`） | `3×176 + 2×12 = 552px` | 176 × 99 恒定 | 再缩一档 | 8 人满员 |
| 7 且焦点格 < 480px，或视口**宽 < 高** | **横条**：rail 移到舞台下方一行（可两行） | 高度 `99px`（两行 210px） | 176 × 99 恒定 | 横向占满、高度留出两行 | 满员 + 窄屏 / 竖屏 |

- 可用高 `H = var(--live-focus-max-height)` = `calc(100vh - 250px)`（r002 既有，含状态条与控制坞让位）。
- 焦点格：`focusW = clamp(var(--focus-min-width-squeeze, 320px), 可用宽, 16/9 × H)`，`focusH = focusW × 9/16`，`margin: 0 auto` 居中 —— 与现状一致，只是把「可用宽」从「视口宽」改成「视口宽 − rail 实际列宽 − gap」。
- **竖屏**（`宽 < 高`）直接走横条模式（与 cp-3 的「侧边栏竖屏缺陷」同源处理：竖屏下把纵向条改为横向条，不再挤压宽度）。

### 7.5 谁出现在 rail 里（决定「框的数量」）

| 人 | 是否在 rail | 理由 |
| --- | --- | --- |
| 焦点人（含共享者） | 否 | 他已在焦点格 |
| 在册且**在线**（已连上 LiveKit） | 是 | 舞台 = 此刻的现场（ADR-0011 条 1） |
| 在册但**离线**（掉线 / 未进房） | 否 | 空头像占位只会缩小有效画面；「谁掉了」在抽屉里看（r002 §4.7 决定） |
| 共享轨本身（ScreenShare） | 否（不进 rail） | 共享只能在焦点格（r002 §4.8，代码已如此） |
| 不在册（离开 / 被移出） | 否 | 不参与实时面 |

### 7.6 变换清单（一场讨论里会发生的每一次尺寸变化）

| 事件 | 尺寸后果 | 动效 | 时长 |
| --- | --- | --- | --- |
| 进房第一人 | 空态 → 焦点格 | 空态淡出 + 焦点格淡入（无位移） | 120 / 240ms |
| 第二人加入 | 焦点格**不变**；rail 出现第 1 格 | 新格淡入 + 6px 上移 | 120ms |
| 第 2、3 个加入（k ≤ 3） | 同上，rail 只是变长（格子尺寸不变） | 同上 | 120ms |
| 第 4 个加入（k = 4） | rail 单列 → **双列**；焦点格缩一档 | rail 宽与焦点格**同帧同步**过渡，不重挂载（key 稳定，不闪烁） | 240ms |
| 第 7 个加入（k = 7） | 双列 → 三列（或转横条）；焦点格再缩 | 同上 + 一次 120ms 交叉淡入避免「跳」 | 240 / 120ms |
| 有人离开 / 掉线 | rail 少一格；跨阈值时列数回退 | 离开格淡出 → 重排 | 120 → 240ms |
| 焦点易手 | 旧焦点**大 → 小**回 rail、新焦点**小 → 大**进主格 | 两侧同帧同步过渡（宽/高/滤镜；**不做平移**） | 240ms |
| 开始 / 结束共享 | 焦点格**内容**换（人 ↔ 共享画面），尺寸不变；rail 不变 | 交叉淡入 | 240ms |
| 静默 30 秒（界面退场） | 尺寸不变，只降透明度 | 既有 | — |
| 房间结束 | 全部消失（跳回列表） | 不特殊处理 | — |
| `prefers-reduced-motion` | 上述过渡全部取消，仅保留不透明度与颜色变化；重排瞬时完成 | — | 0ms |

### 7.7 派生函数：`computeStageLayout`（**唯一**的布局事实源）

```ts
// frontend/src/components/live/stageLayout.ts
export type RailMode = 'none' | 'single' | 'double' | 'triple' | 'strip'
export interface StageLayout {
  focus: { identity: string; kind: 'share' | 'focus' | 'speaker' | 'self' } | null
  rail: { identity: string; speaking: boolean }[]   // 顺序：说话者优先，其次加入顺序
  railMode: RailMode
  metrics: { railWidth: number; railColumns: number; railTile: { w: number; h: number }; focusMaxWidth: number }
}
export function computeStageLayout(input: {
  online: string[]                 // 在线的 identity（含自己；函数内部剔除焦点人）
  selfIdentity: string
  focusUserId: string | null       // 服务端同步的手动焦点（ADR-0014）
  shareIdentity: string | null     // 正在共享的人（无则 null）
  speakerIdentity: string | null
  viewport: { w: number; h: number }
}): StageLayout
```

- 内部顺序：① 先定焦点（`share > manual focus > speaker > self`，ADR-0014）② 再算 `k = 在线人数 − 焦点人` ③ 由 `k` 与 `viewport` 走 §7.4 的尺寸阶梯 ④ 输出 rail 顺序与度量。
- `LiveStage` 只负责渲染 `StageLayout`；**全仓只有这一个函数决定「谁被放大、缩格怎么排」**（原设计里另起的 `pickFocusTile` 已并入，不再另建）。

### 7.8 布局验收口径（写进 review.md 的证据）

| 断言 | 方法 | 期望 |
| --- | --- | --- |
| 尺寸可预期 | 2 / 4 / 6 / 8 人四档截图 + `getBoundingClientRect()` | rail 列数 = 1 / 2 / 2 / 3（或横条）；**缩格恒为 176×99** |
| 焦点格只在两个门槛变 | 依次让第 4、第 7 人加入，量测焦点格宽 | 仅这两次变化；其余加入不变 |
| 焦点易手无跳变 | 双浏览器切换焦点，抓过渡前后两帧 | 240ms 内完成、两侧同帧、无重挂载（DOM 节点 id 稳定） |
| 竖屏 / 窄屏 | 720×1024 与 900×600 截图 | rail 为底部横条、焦点格 ≥ 320px 宽、无横向溢出 |
| 降级 | `prefers-reduced-motion` 模拟 | 重排瞬时完成，无过渡动画 |

## 8. 样式与动效（材质 · 徽标 · 动效 · 令牌）

### 8.1 三条原则（先立规矩，再定细节）

1. **标注只给「人为」的动作**：自动产生的状态（谁在说话）不标注，人为调度的状态（房主给焦点、有人共享）才标注 —— 否则「每说一句话就闪一个徽标」，指示会噪声化。
2. **颜色不做唯一信息通道**：焦点 / 共享 / 举手都必须是「图标 + 文字 + 颜色」三重表达（沿用 `docs/04-style/global-style.md` 的既有条款）；本轮**不新增颜色语义**，全部复用 `--accent`（强调 = 人为关注）与 `--danger`（破坏性）。
3. **零装饰**：不加光斑、不加边框动画、不加阴影堆叠；「更醒目」只准通过**上缘线宽度、降权程度、徽标文字**三处实现。

### 8.2 焦点格与共享格的材质

| 项 | 规格 | 说明 |
| --- | --- | --- |
| 尺寸 | **不在本节定义** —— 由 §7.4 的尺寸阶梯算出（`aspect-ratio`、`max-height` 与 r002 相同） | 尺寸只有一个事实源 |
| 上缘线 | **2px** `--live-focus-glow`（半透明强调色）| 现状即 2px；**共享时 3px**（`--share-accent-line`）以示「这是内容，不是人」 |
| 内发光 | 0 8px 24px `--live-focus-glow`（既有） | 不变 |
| 非焦点格降权 | `saturate(calc(1 - var(--live-focus-dim))) brightness(var(--live-focus-brightness))`（默认 0.35 / 0.88） | r002 既有；**改「谁更醒目」只需调这两个令牌** |
| 切换过渡 | 尺寸与降权均 `var(--focus-switch-duration)`（默认 240ms）+ `var(--ease)` | 不做「弹跳」，不做缩放超过 1.0 |

### 8.3 徽标（`FocusBadge`）—— 复用现有 `.chip` 体系，不新造胶囊

| 项 | 规格 |
| --- | --- |
| 何时出现 | ① 有人共享屏幕 → `共享 · 名称` ② 房主/协管指定了焦点 → `焦点 · 名称`。说话者与自己**不出现徽标**（原则 1） |
| 位置 | 焦点格**左上角**，内缩 `12px`（`--badge-inset: 12px`） |
| 几何 | 复用 `.chip`：`padding 3px 10px` / `border-radius 999px` / `font-size 12px` / `gap 5px` / 图标 14px `strokeWidth 1.75` |
| 材质 | 底 `--live-focus-badge-bg`（默认 `--live-surface`，与状态条同一材质）+ 1px 描边 `--line` |
| 变体 | `.chip-focus`（强调色族，图标 Lucide `Crosshair`）/ `.chip-share`（中性偏亮，图标 Lucide `MonitorUp`） |
| 文字 | 焦点：`焦点 · 王一诺`；共享：`共享 · 王一诺`；自己是那个人的时候写 `焦点 · 你` / `共享 · 你` |
| 失效态 | 焦点人已不在册（`left_at` 非空）→ 徽标不显示（前端派生时该焦点**已失效**，见 §8.5 边界）；共享人断线 → 共享轨消失，徽标随之消失 |
| 可交互性 | 徽标**不是按钮**（避免误点）；停止共享/取消焦点的入口在控制坞与成员行 |

### 8.4 状态条的全局指示（抽屉收起时唯一能看到状态的地方）

| 状态 | 状态条中部信息组显示 | 备注 |
| --- | --- | --- |
| 无焦点、无共享 | **不显示**（不占位） | 保持状态条极简 |
| 有手动焦点 | `[Crosshair 14px] 焦点 王一诺`（`--text-dim` + 名字用 `--text`） | 位于「N / 8 在房间」之后 |
| 有共享 | `[MonitorUp 14px] 共享 王一诺`（同一位置替换） | 共享优先，不并列显示（同 ADR-0014） |
| 焦点/共享人已离开 | 文案变 `焦点已失效`（`--text-mute`，3 秒后自动消失） | 与 §8.5 的回落一致 |

### 8.5 成员行与按钮态（房主/协管视角）

| 元素 | 规格 |
| --- | --- |
| 「给焦点」按钮 | 成员行动作区，位于「设为协管」之后、「更多」之前；文字按钮（`btn btn-ghost btn-sm`）+ Lucide `Crosshair` |
| 已是焦点 | 按钮文案变「取消焦点」，`btn-accent` 态（`--accent-soft` 底 + 强调色描边）——**与「设为协管」的选中表达方式一致**，不引入新语言 |
| 行内标记 | **不做**（原方案的「左侧强调竖条」撤销）：行的「被关注」状态已由按钮文案表达，再加装饰违反原则 3（见 §8.9 必要性） |
| 权限 | 仅房主/协管可见；`connecting` / `reconnecting` 时禁用（沿用 F-16 防呆条③） |

### 8.6 举手与聊天的样式（补齐：本节不只管焦点）

| 元素 | 规格 |
| --- | --- |
| 举手按钮（控制坞左组第三颗） | 未举手：`live-ctrl` 默认态 + Lucide `Hand`；举手中：`live-ctrl-hand-active` —— 底 `--live-hand-active`（强调色 12%）、描边强调色 35%、文案变「放下手」；**图标不切换**（避免闪烁），状态由颜色 + 文字双重表达 |
| 举手列表（抽屉「讨论」tab 顶部、状态条） | 一行为 `Hand 14px` + 名称 + 房主/协管的「放下」；「正在举手」用 `.chip-accent` 表达，与全站徽标同一套 |
| 聊天气泡 | 自己：右对齐、描边 `--chat-bubble-own`（强调色 30%）、底 `--panel-strong`；他人：左对齐、底 `--panel-strong`、描边 `--line-soft`；系统消息：居中、无气泡、`--text-mute`、12px |
| 消息排版 | 正文 13px / 行高 1.6 / `white-space: pre-wrap`（保留换行）；单条最大宽 `min(420px, 78%)` |
| 时间戳 | `HH:mm`，12px `--text-mute`；**只在与前一条间隔 > 5 分钟时显示**（避免每行都挂时间） |
| 输入区 | 单行 36px，最多自动增高到 3 行；右下角 12px 计数 `n/500`；发送失败时气泡下方一条 `--danger` 细线与「重发」文字按钮 |
| 未读徽标 | 状态条「讨论」按钮内的数字形态，复用 `.chip-accent`；超过 9 显示 `9+` |

### 8.7 边界态（必须显式定义，否则实现会各写各的）

| 情形 | 行为 | 理由 |
| --- | --- | --- |
| 焦点人主动离开 / 被移出 / 断线（不再是 `active` 成员） | 前端派生时**忽略该焦点**，焦点格回落下一级；状态条显示「焦点已失效」3 秒 | 放大一块空白头像是纯负面体验；「焦点」的语义是「让在座的人看他」 |
| 焦点人在册但离线（掉线未退出） | **保留焦点**，其格显示既有「离线」呈现（头像块 + 灰显） | 他仍是成员，只是此刻不在；房主可能正等他回来 |
| 焦点 = 自己 | 徽标 `焦点 · 你`；不加额外横幅、不弹任何提示 | 避免"表演感"，且状态条已能看出 |
| 共享与手动焦点并存 | 焦点格 = 共享画面（共享徽标）；状态条 = `共享 名称`；**手动焦点不消失**（取消共享后自动回到焦点） | ADR-0014 的优先级派生 |
| 共享中有人说话 | 焦点格不变（不夺共享） | M3 验收 E12 |
| 重连中（`connecting` / `reconnecting`） | 焦点格保留上一次的派生结果（不闪烁切换）；徽标保留 | 避免网络抖动导致画面乱跳 |
| 房间结束 | 焦点/共享随连接断开而消失；不进归档数据（不落库） | 共享与焦点都是「当场」的事 |

### 8.8 动效总表（全部可降级）

| 动效 | 时长 / 参数 | 说明 |
| --- | --- | --- |
| 焦点切换（尺寸 + 降权） | `--focus-switch-duration`（240ms）+ `--ease` | 一次过渡，不叠加 |
| 焦点格上缘线「展开」 | `--focus-line-in`（300ms，0 → 2px 高度方向） | **一次性**；获得焦点时 |
| 徽标入场 | `var(--t-fast)`（120ms）淡入 + 6px 位移 | 与消息淡入同一套参数 |
| 举手按钮激活脉冲 | 复用 r002 申请徽标手法：一次性 2.4s | 不循环 |
| 消息淡入 | `var(--msg-enter)`（120ms，透明度 + 6px） | 新消息 |
| 降级 | `prefers-reduced-motion: reduce` → 上述位移与展开全部取消，仅保留**不透明度与颜色**变化；脉冲静止 | 与 r002 口径一致（E14） |
| **明确不做** | 获得焦点的「外发光闪烁」（原方案的 600ms glow） | 在暗色专注界面里属于表演性装饰，见 §8.9 |

### 8.9 令牌总表（**唯一来源**；cp-6 落库时照抄进 `global.css` 的 `:root` 与风格指南 §12.1）

| 令牌 | 默认值 | 改它会怎样 |
| --- | --- | --- |
| `--live-rail-width` | `176px`（既有） | 缩格宽（§7.4） |
| `--live-rail-tile-h` | `99px`（**新**） | 缩格高（= 176×9/16，替换「均分 1/3 高」的算法） |
| `--live-rail-max-rows` | `3`（**新**） | 单列最多几格（超过就加列） |
| `--focus-min-width` | `480px`（**新**） | 焦点格最小宽（低于它就转底部横条） |
| `--focus-min-width-squeeze` | `320px`（**新**） | 极窄屏下的兜底最小宽 |
| `--live-focus-dim` | `0.35`（既有） | 非焦点格的降饱和程度 —— 「谁更醒目」的主旋钮 |
| `--live-focus-brightness` | `0.88`（既有） | 非焦点格的降亮 |
| `--live-focus-glow` | `rgba(124,240,196,0.16)`（既有） | 焦点格上缘线与内发光颜色 |
| `--focus-accent-line` / `--share-accent-line` | `2px` / `3px` | 焦点格 / 共享格的上缘线宽 |
| `--focus-switch-duration` | `240ms` | 焦点切换过渡 |
| `--focus-line-in` | `300ms` | 上缘线一次性展开 |
| `--badge-inset` | `12px` | 徽标距焦点格左上角的距离 |
| `--live-focus-badge-bg` | `var(--live-surface)` | 徽标底色材质 |
| `--msg-enter` | `120ms` | 消息与新徽标的入场时长 |

### 8.10 几何与截图验收（写进 review.md 的实测口径）

| 断言 | 量测方法 | 期望 |
| --- | --- | --- |
| 焦点格上缘线宽 | `getComputedStyle(tile).borderTopWidth` | `2px`（共享时 `3px`） |
| 非焦点格降权 | `getComputedStyle(tile).filter` | `saturate(0.65) brightness(0.88)` |
| 徽标几何 | `getBoundingClientRect()` | 高 `24px` 左右（chip 3+3 padding + 12px 字号行高），距格左上各 `12px` |
| 徽标文字 | `innerText` | `焦点 · 王一诺` / `共享 · 王一诺` |
| 零 emoji / 单一图标库 | 扫描 `frontend/src` | 无 emoji；`Crosshair` / `MonitorUp` 均来自 `lucide-react` |
| 截图 | 1265×566（桌面）与 720×1024（窄屏） | 焦点格居中、缩格在右、徽标不遮挡人脸中心区 |
| 降级截图 | DevTools 模拟 `prefers-reduced-motion` | 无位移/展开，仅透明度与颜色变化 |

### 8.11 必要性五轴（每个元素都要先过这一关，能省的省掉）

| 元素 | 功能 | 位置 | 展示 | 提示 | 防呆 | 结论 |
| --- | --- | --- | --- | --- | --- | --- |
| 焦点格上缘线 2px/3px | 标记「这是焦点」 | 格顶 | 线宽区分人与内容 | — | — | **保留**（r002 既有，替代廉价粗边框） |
| 徽标 `焦点 · 名称` | 解释「为什么是他被放大」 | 格左上 | 图标+文字 | 人为 vs 自动 | 非按钮不误点 | **保留**（没有它，观众无从判断是调度还是自动） |
| 状态条指示 | 抽屉收起时仍可见 | 状态条 | 文字 | 失效提示 | — | **保留**（徽标会被共享顶掉） |
| 成员行「给焦点」选中态 | 反馈动作已生效 | 成员行 | 按钮态 | 文案切换 | 重连禁用 | **保留**（与「设为协管」同款表达） |
| 成员行左侧强调竖条 | 装饰性重复 | 成员行 | 装饰 | 重复按钮已表达 | — | **去掉**（违反原则 3） |
| 获得焦点的外发光闪烁 | 表演性 | 格 | 动效 | 无信息增量 | — | **去掉**（只留 300ms 上缘线展开） |
| 焦点「自动失效回落」 | 避免放大空白 | 派生逻辑 | — | 状态条提示 | 防呆 | **保留**（必须显式定义） |

## 9. 教学契约（人可见的使用面）

- **场景一句话**：讨论进行中，大家能打字补充、举手要发言、由房主把发言焦点交给某人、共享屏幕讲材料 —— 而且每个人看到的是同一份现场。
- **入口**：交流页抽屉「讨论」tab（消息）/ 控制坞左组「举手」「共享屏幕」/ 抽屉成员行「给焦点」。
- **输入**：输入框回车发送（≤500 字）；点按钮举手与共享；房主/协管在成员行给焦点。
- **输出**：消息落库并双端一致（刷新不丢）；举手落库并可被房主放下；焦点两浏览器一致；共享画面进焦点格并带徽标。
- **一次典型动作（=验收示范）**：B 发「我先补充一句」→ A 端 1 秒内看到；B 举手 → A 在成员行给 B 焦点 → 两浏览器都放大 B；B 共享屏幕 → 共享画面取代焦点格，A 说话也不夺焦点。
- **开发者扩展点**：加第六个房内能力 = ① 建表（若需持久化）② 三个 service 函数（list/写/连带）③ 一组路由 ④ 一个 hook（复用 `useDataChannel`）⑤ 一个 topic ⑥ 文档四处。照 §5/§6 抄即可，无需碰主循环。

## 10. 验证与取证

### 10.1 E → 验证方式映射（验收条目见需求单 §5）

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

### 10.2 断线重连怎么验（手段、边界、谁做什么）

「断网 5~10 秒后自动回房」这条只能**真断网**才算数；而我的无头浏览器**拿不到真实断网能力**（DevTools 的 Network Offline 不影响 WebRTC 流量，这是 Chromium 的已知限制；busy-loop 冻住 JS 也不会让 ICE 断）。所以把它拆成**三段**，每段的证据强度写清楚，不混：

| 段 | 验什么 | 手段 | 谁做 | 证据强度（写进 review.md 的原话） |
| --- | --- | --- | --- | --- |
| A1 | **状态机与界面**：`Reconnecting` → 状态条「正在重连…」+ 全部按钮禁用；`Reconnected` → 恢复且不退出房内页 | 在页面里**注入 SDK 事件**（`room.emit(RoomEvent.Reconnecting)` / `Reconnected`），需要 dev-only 调试句柄 `window.__lgRoom`（U15） | 我（全自动） | 「**事件注入级**：验证了 UI 与状态机对 SDK 事件的响应，不是真实断网」 |
| A2 | **断开归因四态**：被移出 / 房间结束 / 同账号双开 / 网络断开 → 四种文案 | 注入 `RoomEvent.Disconnected(reason)` 四个取值 + 截图 | 我（全自动） | 「事件注入级（归因映射）」 |
| A3 | **重连失败分支**：彻底连不上 → 显示「连接已断开」+ 重连按钮，且不自动退出 | **本地自建模式**：临时 `LIVEKIT_MODE=self` 起本地 `livekit-server`，我停掉它 8 秒（真实中断，且不碰你的网络） | 我（脚本化） | 「**真实中断**（本地媒体服务器停机 8 秒）；本地服务器重启后房间在内存里已消失，故本条验到的是失败支路」 |
| B1 | **真实断网 8 秒后自动回房 + 声画恢复**（Cloud 主路径，M3/E18 的正条） | 把**页面所在机器的网络**断 8~10 秒再恢复 | **需要你一点操作**（见下） | 「真实断网，双端实拍」 |
| B2 | **重连后设备状态保持**（关摄像头/静音后重连仍保持） | 同 B1；无摄像头时我只能验「状态未回弹」，画面需你真机 | 你点 + 我抓 | 「状态保持：实拍；画面恢复：你真机确认」 |

#### 需要你做的（最低门槛，两种载体二选一）

| 选项 | 你要做的 | 我做什么 | 风险 |
| --- | --- | --- | --- |
| ① **Wi-Fi 开关 / 飞行模式**（推荐） | 点一下网络图标关掉 → 等我的倒计时（约 10 秒）→ 再点回来。**共两次点击** | 我提供 `reconnect-drill.bat`：双击后它把操作写成 3 行大字 + `8` 秒倒计时（不碰你的系统设置），同时我在这 8 秒里每 500ms 抓一次页面状态与截图 | 无（不碰系统设置） |
| ② **一键禁/启网卡脚本**（备选） | 双击 `netcut.bat`（**需要管理员**） | 脚本用 `netsh interface set interface <名字> admin=disabled` 断开、8 秒后 `admin=enabled` 恢复；网卡名由脚本自己列出让你选，不需要你记 | 中：脚本中途被杀会留下断网状态（脚本内做「异常也要恢复」的兜底），且只有一块网卡有效 |
| ③ 不配合 | 什么都不用做 | 只跑 A1~A3 | 无 B 段证据：review.md 里「断网重连」只能标为**事件注入级**，我不会写成「真断网验证过」 |

#### 一起要验的四条断言（B1 时我抓什么）

| 时点 | 抓什么 | 期望 |
| --- | --- | --- |
| 断网后 ~1~3 秒 | 状态条文案 + `.live-dock` 按钮 `disabled` | `正在重连…`；麦克风/摄像头/举手/共享全部禁用 |
| 断网 8 秒中 | 页面是否还在 `/rooms/:id/live`、是否弹错 | 不退出房内页、不弹 toast |
| 恢复后 ~1~5 秒 | 状态条 + `connection.status` | `已连接`（自动，无需点按钮） |
| 恢复后 | SQL：`room_members` 该房行数 | 与断网前一致（不新增成员记录） |

#### 另外两条约束

- 我的抓取用**我自己的无头浏览器**（不抢你的前台）；B1 需要**你机器断网**，所以断网期间我这台也要能继续跑（我在本机，网络断了我也没法连你自己开的 `5173`……）→ **修正做法**：B1 用**你的浏览器窗口**（你本来就开着 `localhost:5173`）做操作与观察，我在**本机侧**用 `curl`/SQL 与你的截图对账；或者由你把 `dev.bat` 起的两个窗口留着，我用本机回环不受影响 —— 因为断网只影响出网，`127.0.0.1` 的 dev 服务照常，所以我的无头浏览器仍能连 `localhost:5173`，只是它自身也会断网 → 它测到的就是「真的断了」。**结论：A+B1 我都能在自己浏览器里跑，你只需要把 Wi-Fi 关一下再打开。**
- U15 的 `window.__lgRoom` 只在 `import.meta.env.DEV` 下挂载，**生产构建不含**（构建后 `git grep __lgRoom` 应只在源码命中），这条要在 cp-5 的提交里验证。

## 11. 回退方案

- 逐 cp `revert`（append-only，禁 reset）：cp-6 回退 → 界面回到 r003（后端接口留着不影响）；cp-4 回退 → 去掉 5 组路由，两张新表**保留**（空表不影响 r003 版本运行，也不破坏 r002/r003 的既有测试）；
- 迁移不可逆部分：无（只增表、无列改写），`db_init --reset --seed` 可重建；
- 若优先级规则被推翻（ADR-0014 变更）：只需改 `computeStageLayout`（§7.7）一处 + 文档，不牵动数据层。

## 12. 风险与不确定

| 项 | 说明 | 处置 |
| --- | --- | --- |
| 服务端强停共享是否可行 | §6.2 待实测 | cp-6 前实测；不可行则保持协作停止并写进文档 |
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
| 2026-09-19 | cp-4-1 | L1 | SQL 落点改到新文件 `repositories/room_extras.py`（设计只点名了 service/router，未提仓储层） | 采纳：与 `repositories/rooms.py` 同层，不把 400+ 行的既有文件再撑大 |
| 2026-09-19 | cp-4-2 | L1 | 错误码 `INVALID_INPUT` → **`VALIDATION`**（空/超长/非法游标） | 采纳：不发明新码，复用 r001 错误码总表 |
| 2026-09-19 | cp-4-3 | L2 | 读取接口对 `ended` 房间**也返回 409**（设计原话是「除 GET 外一律 409」） | 采纳（收窄）：M3 无归档面，读取只服务进行中的房间；M4 归档按 `r003-ahead-m4-ended-rooms-archive.md` §3.1 另开只读面 |
| 2026-09-19 | cp-4-4 | L1 | `clear_hands_for_room_end` 折进 `rooms.end_room`（直接调仓储） | 采纳：避免 `rooms ↔ hands` service 层循环 import |
| 2026-09-19 | cp-4-5 | L2 | 修 `migrate.split_statements`：过滤迁移文件内的事务控制语句 | 必须：`003_` 文件自带的 `BEGIN/COMMIT` 与外层 savepoint 冲突，导致迁移中止且不记版本（r002 遗留、本轮暴露） |
| 2026-09-19 | — | **文档整理（本轮，L1，无行为变化）**：新增 §0 导航与单一事实源表；§7 由「焦点优先级」扩为「舞台结构与布局动力学」（7.1~7.8，原 §7.5 的下挂小节提升为同级）；§8 重排为 8.1~8.11 并**合并两张令牌表为 §8.9 唯一来源**；补齐 §8.6「举手与聊天的样式」（原标题名不副实）；§10 拆为 10.1 映射 + 10.2 断线；统一函数名为 `computeStageLayout`（删去 `pickFocusTile` 的另立说法）；修正 §6.1/§6.2 编号与全页引用 | 用户「你的文档写的开始混乱了，解决这个先」 |
