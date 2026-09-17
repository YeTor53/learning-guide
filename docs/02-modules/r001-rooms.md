---
title: r001 房间功能详细设计（模块页）
description: 房间的生命周期、业务规则、PostgreSQL 数据模型、接口、后端与前端函数级实现路径、并发边界与验证。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-17
---

<!-- overview -->
本页是**房间功能**的单一事实源：领域规则、数据模型、接口、逐文件函数级实现路径、并发与边界、验证矩阵。
不在本页重复的：结果信封与后端目录总览（以重写后的 `docs/01-architecture/r001-app-architecture.md` 为准）、项目方向与里程碑（`docs/00-project/global-roadmap.md`）、纪要（`docs/02-modules/r001-summaries.md`）。
本文对三项待拍板保持中立，只在 §10 标出分支点：LiveKit 来源（P3′）、PostgreSQL 落地（P9）、后端框架与迁移工具（P10）。

> 功能行为、交互状态、按钮与提示文案以 **功能页** `docs/02-modules/r001-rooms-features.md` 为准；本页只讲怎么实现（数据模型 / 接口 / 函数路径）。

## 1. 范围与里程碑归属

| 项 | 里程碑 | 本文是否给到实现级 |
| --- | --- | --- |
| 建房（主题/标题/简介）、列表、详情 | M1 | ✅ |
| 加入申请：提交 / 列表 / 批准 / 拒绝 | M1 | ✅ |
| 离开房间、结束房间（含连带动作） | M1 | ✅ |
| 房间码生成与邀请（限时链接/房间码 + 过期） | M2 | ✅（表与函数已定，API 属 M2） |
| 踢人（服务端强制断开）、角色任命、Host 移交 | M2 | ✅（签名已定，实现属 M2） |
| 入房环节「房间已满」提示、举手与焦点（LiveKit 自定义能力） | M2/M3 | 不在本文（见能力页） |

明确不做：房间删除、重开已结束房间、房间自动结束、公网部署、多租户。

## 2. 领域模型

**存储态（`rooms.status`，唯一事实源）**：`active`（开放）→ `ended`（终态）。

**派生相位（不落库）**：`active.idle`（房内无人）、`active.in_session`（房内 ≥1 人）、`ended`。
- M1：`derive_room_phase` 只区分 `active.idle` / `ended`。
- M2：接 LiveKit 在场信息补 `in_session`（函数签名不变）。

**实体关系**：`users 1—N rooms`（host）；`rooms 1—N room_members N—1 users`；`rooms 1—N join_requests N—1 users`；`rooms 1—N invites`；`rooms 1—N chat_messages`；`rooms 1—1 session_summaries`。

**成员退出语义（单源）**：`room_members.status ∈ {active, inactive}` + `exit_reason ∈ {self_leave, kicked, room_ended}`，并用 CHECK 强制两者一致（`active` 必须无 `exit_reason`/`left_at`，`inactive` 必须两者都有）。

## 3. 数据模型（PostgreSQL）

> `session_summaries`（纪要表）属纪要模块，定义见 `docs/02-modules/r001-summaries.md` §3（单一事实源，不在此复制）。

```sql
-- 001_schema.sql（逐字落库；PostgreSQL 15+）
CREATE TABLE IF NOT EXISTS schema_migrations (
  version    TEXT PRIMARY KEY,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
  id            TEXT PRIMARY KEY,
  email         TEXT NOT NULL,
  display_name  TEXT NOT NULL CHECK (char_length(display_name) BETWEEN 1 AND 32),
  password_hash TEXT NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_users_email_lower ON users (lower(email));

CREATE TABLE IF NOT EXISTS rooms (
  id          TEXT PRIMARY KEY,
  host_id     TEXT NOT NULL REFERENCES users(id),
  topic       TEXT NOT NULL CHECK (topic IN ('epicureanism','math-biology','german-history','custom')),
  topic_label TEXT NOT NULL CHECK (char_length(topic_label) BETWEEN 1 AND 32),
  title       TEXT NOT NULL CHECK (char_length(title) BETWEEN 1 AND 80),
  description TEXT NOT NULL DEFAULT '' CHECK (char_length(description) <= 500),
  status      TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','ended')),
  capacity    SMALLINT NOT NULL DEFAULT 8 CHECK (capacity BETWEEN 2 AND 8),
  room_code   TEXT NOT NULL UNIQUE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  ended_at    TIMESTAMPTZ,
  CHECK ((status = 'active' AND ended_at IS NULL) OR (status = 'ended' AND ended_at IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS ix_rooms_status_created ON rooms (status, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_rooms_topic ON rooms (topic, status);

CREATE TABLE IF NOT EXISTS room_members (
  id          TEXT PRIMARY KEY,
  room_id     TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
  user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role        TEXT NOT NULL CHECK (role IN ('host','moderator','participant')),
  status      TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive')),
  exit_reason TEXT CHECK (exit_reason IN ('self_leave','kicked','room_ended')),
  joined_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  left_at     TIMESTAMPTZ,
  CHECK ((status = 'active'   AND exit_reason IS NULL     AND left_at IS NULL)
      OR (status = 'inactive' AND exit_reason IS NOT NULL AND left_at IS NOT NULL))
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_room_members_active
  ON room_members (room_id, user_id) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS ix_room_members_room_active ON room_members (room_id, role) WHERE status = 'active';

CREATE TABLE IF NOT EXISTS join_requests (
  id         TEXT PRIMARY KEY,
  room_id    TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
  user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  status     TEXT NOT NULL DEFAULT 'pending'
             CHECK (status IN ('pending','approved','rejected','withdrawn','cancelled')),
  message    TEXT NOT NULL DEFAULT '' CHECK (char_length(message) <= 200),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  decided_at TIMESTAMPTZ,
  decided_by TEXT REFERENCES users(id),
  CHECK ((status = 'pending' AND decided_at IS NULL) OR (status <> 'pending' AND decided_at IS NOT NULL))
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_join_requests_pending
  ON join_requests (room_id, user_id) WHERE status = 'pending';

CREATE TABLE IF NOT EXISTS invites (
  id         TEXT PRIMARY KEY,
  room_id    TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
  code       TEXT NOT NULL UNIQUE,
  created_by TEXT NOT NULL REFERENCES users(id),
  expires_at TIMESTAMPTZ NOT NULL,
  max_uses   SMALLINT NOT NULL DEFAULT 8 CHECK (max_uses BETWEEN 1 AND 8),
  used_count SMALLINT NOT NULL DEFAULT 0 CHECK (used_count >= 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_invites_room ON invites (room_id, expires_at DESC);

CREATE TABLE IF NOT EXISTS chat_messages (
  id         TEXT PRIMARY KEY,
  room_id    TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
  user_id    TEXT NOT NULL REFERENCES users(id),
  body       TEXT NOT NULL CHECK (char_length(body) BETWEEN 1 AND 2000),
  kind       TEXT NOT NULL DEFAULT 'chat' CHECK (kind IN ('chat','system')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_chat_messages_room_time ON chat_messages (room_id, created_at DESC);
```

时间字段一律 `TIMESTAMPTZ`；ID 一律 `TEXT` 带前缀（`usr_`/`room_`/`mem_`/`req_`/`inv_`/`msg_`），由应用生成，便于日志与人工核对。

## 4. 业务规则（逐操作：触发者 / 前置 / 规则 / 副作用 / 错误码）

| 操作 | 触发者 | 前置与规则 | 副作用（同事务） | 错误码 |
| --- | --- | --- | --- | --- |
| 建房 | 任意登录用户 | 主题 ∈ 4 值；标题 1–80 字；简介 ≤500 字；`capacity` 固定 8（可留参） | 锁无需；写 `rooms`（生成 `room_code`，冲突重试 3 次）+ 写 `room_members(host, active)` | `VALIDATION` |
| 列表 | 任何人 | `status` ∈ {active,ended,all}；`topic` 可选；`mine=1` 需登录 | 只读；聚合 `member_count`/`pending_count`/`my_role`/`my_request` | `VALIDATION` |
| 详情 | 任何人 | 房间存在 | 只读；房间 + 活跃成员 + 最近 20 条消息 + 我的状态 | `NOT_FOUND` |
| 提交申请 | 登录用户 | 房间 `active`；非活跃成员；无 `pending` | 写 `join_requests(pending)` | `ROOM_ENDED` / `ALREADY_MEMBER` / `ALREADY_PENDING` |
| 看申请列表 | Host/Moderator | 房间存在 | 只读（`status` 可选过滤） | `FORBIDDEN` |
| 批准 | Host/Moderator | 房间 `active`；申请 `pending`；活跃人数 < `capacity` | **锁 `rooms` 行** → 写成员 `participant/active` + 申请置 `approved`（`decided_by=actor`） | `FORBIDDEN` / `ROOM_ENDED` / `ROOM_FULL` / `ALREADY_MEMBER` / `CONFLICT` |
| 拒绝 | Host/Moderator | 房间 `active`；申请 `pending` | 申请置 `rejected`（`decided_by=actor`） | `FORBIDDEN` / `ROOM_ENDED` / `CONFLICT` |
| 建邀请 | Host/Moderator | 房间 `active`；TTL ∈ [5, 1440] 分钟 | 写 `invites`（`code` 6 位、`expires_at`、`max_uses`） | `FORBIDDEN` / `ROOM_ENDED` |
| 用邀请 | 登录用户 | 邀请未过期、`used_count < max_uses`、房间 `active`、非活跃成员 | `used_count += 1` + 写成员（或直接进入申请流程，见 R-2） | `INVITE_INVALID` / `ROOM_ENDED` / `ALREADY_MEMBER` |
| 离开 | 本人（非 Host） | 房间 `active`；是活跃成员 | 成员置 `inactive/self_leave` + `left_at` | `NOT_MEMBER` / `HOST_CANNOT_LEAVE` / `ROOM_ENDED` |
| 结束房间 | **仅 Host** | 房间 `active` | **锁 `rooms` 行**：① `status=ended`、`ended_at`；② 全部活跃成员 → `inactive/room_ended`；③ 全部 `pending` 申请 → `cancelled`（`decided_by=NULL` 表示系统）；④ 提交后（M2）：`delete_room` 强制断开；⑤ 提交后（M4）：触发纪要生成 | `FORBIDDEN` / `ROOM_ENDED` |
| 踢人（M2） | Host/Moderator | 目标为活跃成员且非 Host | 成员置 `inactive/kicked`；事务提交后调 LiveKit 移除参与者 | `FORBIDDEN` / `NOT_MEMBER` / `ROOM_ENDED` |
| 改角色（M2） | Host | 目标为活跃成员 | 更新 `role`（`participant↔moderator`） | `FORBIDDEN` |
| 移交 Host（M2） | Host | 目标为活跃成员 | 双方 `role` 互换（Host ↔ Moderator/Participant） | `FORBIDDEN` |

角色权限矩阵与生命周期转移细节沿用已确认口径（三个角色 × `active`/`ended` 两态），已在 `global-roadmap.md` §2 与本文 §4 表内完全覆盖，不再另开一节复制。

## 5. 接口清单（本模块）

信封 `{ok, data}` / `{ok, error:{code,message}}` 与错误码总表见架构页；本模块路径：

| 方法 | 路径 | 权限 | 请求 | 成功 |
| --- | --- | --- | --- | --- |
| GET | `/api/rooms` | 公开 | `?status=active\|ended\|all&topic=&mine=1&limit=20&offset=0` | 200 `{rooms: RoomListItem[], total}` |
| POST | `/api/rooms` | 登录 | `{topic, topicLabel, title, description?}` | 201 `RoomVO & {myRole}` |
| GET | `/api/rooms/{room_id}` | 公开 | — | 200 `RoomDetail` |
| POST | `/api/rooms/{room_id}/join-requests` | 登录 | `{message?}` | 201 `JoinRequestVO` |
| GET | `/api/rooms/{room_id}/join-requests` | Host/Moderator | `?status=pending` | 200 `{requests: JoinRequestVO[]}` |
| POST | `/api/join-requests/{request_id}/approve` | Host/Moderator | — | 200 `{request, member}` |
| POST | `/api/join-requests/{request_id}/reject` | Host/Moderator | — | 200 `{request}` |
| POST | `/api/rooms/{room_id}/leave` | 活跃成员 | — | 200 `{}` |
| POST | `/api/rooms/{room_id}/end` | Host | — | 200 `RoomVO` |
| POST | `/api/rooms/{room_id}/invites` | Host/Moderator | `{ttlMinutes, maxUses?}` | 201 `{code, expiresAt, url}` （M2） |
| POST | `/api/invites/{code}/redeem` | 登录 | — | 200 `{room, member}` 或 202 `{request}` （M2，形态见 R-2） |
| POST | `/api/rooms/{room_id}/members/{user_id}/kick` | Host/Moderator | — | 200 `{}` （M2） |
| PATCH | `/api/rooms/{room_id}/members/{user_id}` | Host | `{role}` | 200 `MemberVO` （M2） |
| POST | `/api/rooms/{room_id}/transfer-host` | Host | `{userId}` | 200 `{members}` （M2，见 R-4） |

## 6. 后端实现路径（逐文件：函数签名 + 职责 + 返回）

```
backend/
├─ app/db/sql/001_schema.sql          # §3 的 DDL（逐字）
├─ app/db/sql/002_seed.sql            # 演示账号 3 个、示例房间 3 个、历史消息 12 条、1 个已结束房间 + 纪要
├─ app/db/pool.py                     # 连接池
├─ app/db/migrate.py                  # 迁移与种子
├─ app/repositories/rooms.py          # 本模块全部 SQL 绑定
├─ app/services/rooms.py              # 本模块业务规则
├─ app/services/livekit.py            # Token 签发与房间管控（M2 用，签名先定）
├─ app/schemas/rooms.py               # 请求/响应模型
├─ app/api/routers/rooms.py           # 路由薄壳
├─ app/api/deps.py                    # 依赖：当前用户、数据库连接
└─ scripts/db_init.py, scripts/smoke.py
```

### 6.1 `app/db/pool.py`

| 函数 | 签名 | 职责 / 返回 |
| --- | --- | --- |
| `init_pool` | `(dsn: str) -> None` | 建 `psycopg_pool.ConnectionPool`（`min_size=1, max_size=8`），进程内单例 |
| `get_conn` | `() -> Iterator[Connection]` | 上下文管理器：从池借连接，`autocommit=False`，退出时归还（异常时回滚） |
| `close_pool` | `() -> None` | 关池（脚本/测试收尾） |

### 6.2 `app/db/migrate.py`

| 函数 | 签名 | 职责 / 返回 |
| --- | --- | --- |
| `run_migrations` | `(conn: Connection) -> list[str]` | 按文件名顺序执行 `sql/*.sql`，已记入 `schema_migrations` 的跳过；返回本次应用的版本名列表 |
| `reset_schema` | `(conn: Connection) -> None` | `DROP TABLE ... CASCADE` 全部业务表（仅 `--reset` 显式调用） |
| `seed` | `(conn: Connection) -> dict[str, int]` | 执行 `002_seed.sql`（`ON CONFLICT DO NOTHING`，固定 ID 幂等），返回各表行数 |
| `table_counts` | `(conn: Connection) -> dict[str, int]` | 各表 `count(*)`，供 `db_init` 打印证据 |

### 6.3 `app/repositories/rooms.py`（SQL 绑定，全部 `(conn, ...)` 首参）

| 函数 | 签名 | 职责 / 返回 |
| --- | --- | --- |
| `insert_room` | `(conn, row: NewRoom) -> None` | 写 rooms |
| `lock_room` | `(conn, room_id: str) -> RoomRow \| None` | `SELECT ... FROM rooms WHERE id=%s FOR UPDATE`：房间级互斥（批准/结束/踢人/移交共用） |
| `get_room` | `(conn, room_id: str) -> RoomRow \| None` | 读房间 |
| `list_rooms` | `(conn, f: RoomFilter) -> tuple[list[RoomRow], int]` | 列表 + 总数；含状态/主题/`host_id`/分页 |
| `room_aggregates` | `(conn, room_ids: list[str]) -> dict[str, tuple[int,int]]` | 批量取 (活跃成员数, 待批申请数)，避免列表 N+1 |
| `update_room_ended` | `(conn, room_id: str, at: datetime) -> None` | `status='ended', ended_at=%s` |
| `insert_member` | `(conn, row: NewMember) -> None` | 写活跃成员 |
| `get_active_member` | `(conn, room_id: str, user_id: str) -> MemberRow \| None` | 权限判定 |
| `count_active_members` | `(conn, room_id: str) -> int` | 上限与展示 |
| `list_members` | `(conn, room_id: str, include_inactive: bool = False) -> list[MemberRow]` | 成员列表（历史含 `exit_reason`） |
| `deactivate_member` | `(conn, room_id: str, user_id: str, reason: str, at: datetime) -> None` | 单成员退出 |
| `deactivate_all_members` | `(conn, room_id: str, at: datetime) -> int` | 房间结束时批量 `room_ended`；返回受影响行数 |
| `update_member_role` | `(conn, room_id: str, user_id: str, role: str) -> None` | 改角色/移交 |
| `insert_join_request` | `(conn, row: NewJoinRequest) -> None` | 写申请（部分唯一索引兜底并发） |
| `get_join_request` | `(conn, request_id: str) -> JoinRequestRow \| None` | 批准/拒绝 |
| `get_pending_request` | `(conn, room_id: str, user_id: str) -> JoinRequestRow \| None` | 重复申请判定 |
| `list_join_requests` | `(conn, room_id: str, status: str \| None) -> list[JoinRequestRow]` | 申请列表 |
| `decide_join_request` | `(conn, request_id: str, status: str, decided_by: str \| None, at: datetime) -> None` | 落决定（`decided_by=None` 表示系统） |
| `cancel_pending_requests` | `(conn, room_id: str, at: datetime) -> int` | 房间结束时批量 `cancelled`；返回行数 |
| `insert_invite` | `(conn, row: NewInvite) -> None` | 写邀请 |
| `get_invite_by_code` | `(conn, code: str) -> InviteRow \| None` | 校验邀请 |
| `bump_invite_used` | `(conn, invite_id: str) -> int` | `used_count += 1`（`WHERE used_count < max_uses`，返回受影响行数，0 表示已用尽） |
| `list_recent_messages` | `(conn, room_id: str, limit: int) -> list[MessageRow]` | 详情页最近消息（纪要复用） |

### 6.4 `app/services/rooms.py`（业务规则，唯一写库入口）

| 函数 | 签名 | 职责 / 返回 |
| --- | --- | --- |
| `create_room` | `(conn, actor: User, data: CreateRoomIn) -> RoomWithRole` | 校验 → 生成 `room_code`（冲突重试 3 次）→ 写房间 + Host 成员 → 返回房间与我的角色 |
| `list_rooms` | `(conn, actor: User \| None, f: RoomFilter) -> tuple[list[RoomListItem], int]` | 聚合成员数/待批数/我的角色与申请状态 |
| `get_room_detail` | `(conn, actor: User \| None, room_id: str) -> RoomDetail` | 房间 + 成员 + 最近 20 条消息 + 我的状态；不存在抛 `NOT_FOUND` |
| `derive_room_phase` | `(conn, room_id: str) -> str` | `active.idle` / `active.in_session`（M2）/ `ended` |
| `request_join` | `(conn, actor: User, room_id: str, message: str) -> JoinRequestVO` | `assert_room_active` → 非成员 → 无 pending → 写申请；唯一冲突转 `ALREADY_PENDING` |
| `list_join_requests` | `(conn, actor: User, room_id: str, status: str \| None) -> list[JoinRequestVO]` | `assert_room_role(host, moderator)`（房间可 `ended`，只读） |
| `approve_join_request` | `(conn, actor: User, request_id: str) -> Approval` | `lock_room` → 房间 `active` → 申请 `pending` → 人数 < `capacity` → 写成员 + 落决定 |
| `reject_join_request` | `(conn, actor: User, request_id: str) -> JoinRequestVO` | `lock_room` → `active` → 申请 `pending` → 落决定 |
| `create_invite` | `(conn, actor: User, room_id: str, ttl_minutes: int, max_uses: int) -> InviteVO` | `assert_room_role(host, moderator)` → 写邀请 |
| `redeem_invite` | `(conn, actor: User, code: str) -> RedeemResult` | 校验未过期/未用尽/房间 `active`/非成员 → 形态见 R-2 |
| `leave_room` | `(conn, actor: User, room_id: str) -> None` | `lock_room` → `active` → 活跃成员 → 非 Host → `deactivate_member(self_leave)` |
| `end_room` | `(conn, actor: User, room_id: str) -> RoomVO` | `lock_room` → `assert_room_role(host)` → `active` → `update_room_ended` + `deactivate_all_members` + `cancel_pending_requests`（同事务）→ 提交后副作用（M2 `delete_room`、M4 纪要） |
| `kick_member` | `(conn, actor: User, room_id: str, user_id: str) -> None` | `lock_room` → `assert_room_role(host, moderator)` → 目标活跃且非 Host → `deactivate_member(kicked)` → 提交后 `livekit.remove_participant` （M2） |
| `set_member_role` | `(conn, actor: User, room_id: str, user_id: str, role: str) -> MemberVO` | `assert_room_role(host)` → 目标活跃 → 改角色（M2） |
| `transfer_host` | `(conn, actor: User, room_id: str, user_id: str) -> list[MemberVO]` | `assert_room_role(host)` → 双方角色互换（M2） |
| `assert_room_active`（内部） | `(room: RoomRow \| None) -> RoomRow` | 存在否则 `NOT_FOUND`；`active` 否则 `ROOM_ENDED` |
| `assert_room_role`（内部） | `(conn, actor: User \| None, room_id: str, allowed: Sequence[str]) -> MemberRow` | 未登录 `UNAUTHORIZED`；非活跃成员 `FORBIDDEN`；角色不符 `FORBIDDEN` |

事务约定：`create_room / approve_join_request / reject_join_request / leave_room / end_room / kick_member / set_member_role / transfer_host / redeem_invite` 全部在**单个事务**内完成（service 内 `with conn.transaction():`）；只读函数不显式开事务。

### 6.5 `app/services/livekit.py`（M2 用；签名与分支先定）

| 函数 | 签名 | 职责 / 返回 |
| --- | --- | --- |
| `issue_token` | `(room_id: str, user: User, role: str, ttl_seconds: int = 3600) -> str` | 用 `AccessToken(...).with_identity(user.id).with_name(user.display_name).with_grants(VideoGrants(room_join=True, room=room_id, can_publish=True, can_publish_data=True, room_admin=(role=='host')))` + `with_room_config(RoomConfiguration(max_participants=8))` 签 JWT；**Secret 只在此模块读环境变量** |
| `remove_participant` | `(room_id: str, user_id: str, revoke: bool = True) -> None` | 调 `LiveKitAPI.room.remove_participant`；**分支（P3′）**：Cloud 传 `revoke_token_ts=now` 使已签发 Token 立即失效；自建下该字段无同等效果 → 依赖 `issue_token` 的短 TTL（建议 5 分钟）+ 拒绝再签发（见 §10） |
| `delete_room` | `(room_id: str) -> None` | 房间结束时强制断开全部连接（`room.delete_room`） |
| `list_participants` | `(room_id: str) -> list[str]` | 房间内在场的 identity 列表（派生相位 `in_session` 与演示取证） |

### 6.6 `app/schemas/rooms.py`（Pydantic v2）

| 模型 | 字段 | 说明 |
| --- | --- | --- |
| `CreateRoomIn` | `topic: Literal[...]`, `topic_label: str`, `title: str`, `description: str = ""` | 长度约束与 §4 一致 |
| `JoinRequestIn` | `message: str = ""` | ≤200 字 |
| `InviteIn` | `ttl_minutes: int`, `max_uses: int = 8` | TTL ∈ [5,1440] |
| `RoleIn` | `role: Literal["moderator","participant"]` | 改角色 |
| `UserVO` / `MemberVO` / `RoomVO` / `RoomListItem` / `RoomDetail` / `JoinRequestVO` / `InviteVO` | 见架构页字段表 | 出参只暴露 VO，不吐库行 |

### 6.7 `app/api/routers/rooms.py` + `app/api/deps.py`

| 文件 | 函数 | 职责 |
| --- | --- | --- |
| `deps.py` | `current_user_optional()`, `current_user()` | 从会话 Cookie/Bearer 解析用户（会话方案见架构页 §7 的分支决定） |
| `deps.py` | `db_conn()` | 每请求一个连接（`with get_conn() as conn: yield conn`） |
| `routers/rooms.py` | `list_rooms`, `create_room`, `get_room`, `create_join_request`, `list_join_requests`, `approve_request`, `reject_request`, `leave_room`, `end_room`, `create_invite`, `redeem_invite`, `kick_member`, `patch_member`, `transfer_host` | 每个 5–15 行：取依赖 → 调 service → `to_response`；异常由全局 handler 统一转信封 |

### 6.8 脚本

| 脚本 | 行为 |
| --- | --- |
| `scripts/db_init.py` | `--reset/--seed` → `run_migrations` → `seed` → 打印 `table_counts()`（真实输出即验收证据） |
| `scripts/smoke.py` | 走真实 HTTP：注册两个账号 → 登录 → A 建房 → 列表含新房间 → B 申请 → A 批准 → 详情成员=2 → B 离开 → 再次申请/批准 → A 结束房间 → 校验 `status=ended`、成员全 `inactive/room_ended`、申请 `cancelled`；每步打印状态码与关键字段，失败非 0 退出 |

## 7. 前端实现路径（React）

```
frontend/src/
├─ api/http.ts        # 信封解析与错误映射
├─ api/rooms.ts       # 房间接口封装
├─ hooks/useRooms.ts  # 列表查询
├─ hooks/useRoomDetail.ts
├─ pages/RoomsPage.tsx  NewRoomPage.tsx  RoomDetailPage.tsx
└─ components/RoomCard.tsx  RoomForm.tsx  JoinRequestList.tsx  MemberList.tsx  InviteDialog.tsx
```

| 文件 | 导出 | 职责 / 返回 |
| --- | --- | --- |
| `api/http.ts` | `request<T>(path: string, init?: RequestInit): Promise<T>`；`ApiError { code, message, status }` | 拼 baseURL、`credentials: 'include'`、解析 `{ok,data|error}`，`ok=false` 抛 `ApiError` |
| `api/rooms.ts` | `listRooms(params): Promise<{rooms, total}>`、`createRoom(body)`、`getRoom(id)`、`requestJoin(id, body)`、`listJoinRequests(id, status?)`、`approveRequest(rid)`、`rejectRequest(rid)`、`leaveRoom(id)`、`endRoom(id)`、`createInvite(id, body)` | 与 §5 接口一一对应 |
| `hooks/useRooms.ts` | `useRooms(filter)` → `{data, isLoading, error, refetch}` | TanStack Query，`refetchInterval` 见 R-1 |
| `hooks/useRoomDetail.ts` | `useRoomDetail(id)`；`useRoomMutations(id)` → `{requestJoin, approve, reject, leave, endRoom, createInvite}` | 变更后 `invalidateQueries(['room', id])` 与 `['rooms']` |
| `pages/RoomsPage.tsx` | `RoomsPage` | 列表 + 状态/主题筛选 + 「建房」入口（未登录引导登录） |
| `pages/NewRoomPage.tsx` | `NewRoomPage` | 建房表单（主题下拉 + 标题 + 简介）；未登录重定向 `/login?next=/rooms/new` |
| `pages/RoomDetailPage.tsx` | `RoomDetailPage` | 房间信息、成员（含退出原因）、待批申请（Host/Moderator 显示批准/拒绝）、最近消息、邀请入口（M2）、结束房间（Host）、加入/离开按钮（按状态禁用并显示原因） |
| `components/*.tsx` | `RoomCard`、`RoomForm`、`JoinRequestList`、`MemberList`、`InviteDialog` | 纯展示 + 回调，状态与请求由 hooks 提供 |

前端不自行判定权限：按钮可见性按 `myRole`/`myRequest` 渲染，**最终判定一律在服务端**；被拒时用 `ApiError.code` 显示对应中文提示（如「房间已满（上限 8 人）」）。

## 8. 并发、边界与失败

| 场景 | 处理 |
| --- | --- |
| 两人同时批准最后一个名额 | 批准前 `lock_room`（房间级互斥）→ 计数校验 → 第二个请求拿到锁后计数已满，返回 `ROOM_FULL` |
| 同人重复提交申请（含并发双击） | 部分唯一索引 `ux_join_requests_pending` 兜底；捕获 `UniqueViolation` → `ALREADY_PENDING` |
| 结束房间与批准并发 | 两者都先 `lock_room`；后到者看到 `status='ended'` → `ROOM_ENDED`，不会产生「已结束房间新增成员」 |
| 8 人上限的三道闸 | ① 批准时应用层校验；② Token 内 `room_config.max_participants=8` 由 LiveKit 硬限；③ 客户端连接失败时前端显示「房间已满」 |
| 房间码 / 邀请码冲突 | 生成后插入失败重试 3 次，仍失败返回 `INTERNAL` 并记日志 |
| 邀请过期 / 用尽 | `expires_at < now()` 或用尽 → `INVITE_INVALID`；房间 `ended` 时邀请一律 `ROOM_ENDED`（不删邀请行） |
| Host 想离开 | `HOST_CANNOT_LEAVE`，提示「先结束房间或移交 Host」（移交见 R-4） |
| 重复结束房间 | 锁内检查 `status='active'` → `ROOM_ENDED`；不触发二次副作用（纪要 `UNIQUE(room_id)` 防重） |
| 外部服务失败（M2 的 `delete_room`） | 数据库事务已提交，失败只记日志；房间状态不受影响（房间结束是用户意图） |
| 数据库连接中断 | 连接池在借出前检测失效连接；`OperationalError` 映射 `INTERNAL` 并在响应中不回显 DSN |
| 长文本与注入 | 描述/消息长度由 CHECK 与 Pydantic 双重约束；SQL 全参数化，禁止字符串拼 SQL |

## 9. 验证矩阵

| 层 | 对象 | 判据 |
| --- | --- | --- |
| 迁移 | `python scripts/db_init.py --reset --seed` | 打印 7 张表行数：`users≥3`、`rooms≥3`、`chat_messages≥12`、`session_summaries≥1` |
| 单元/集成（pytest） | `tests/test_rooms_service.py` | 建房写 Host 成员（1 条 `active`）；重复申请→`ALREADY_PENDING`；`capacity` 满→`ROOM_FULL`（塞 8 人后第 9 个被拒）；`end_room` 后成员全 `inactive/room_ended`、`pending` 全 `cancelled`；非 Host `end_room`→`FORBIDDEN`；`HOST_CANNOT_LEAVE`；已结束房间 `request_join`→`ROOM_ENDED` |
| 并发 | `tests/test_rooms_concurrency.py` | 两个线程同时批准最后一个名额：恰好 1 个成功、1 个 `ROOM_FULL`，库中活跃成员数 = `capacity` |
| 冒烟（真实 HTTP） | `python scripts/smoke.py` | 每步状态码符合预期，末尾打印 `PASS n/n` |
| 手工演示 | 两个浏览器 | A 建房 → B 申请 → A 批准 → B 详情见自己为成员；房间满 8 人时第 9 人提示「房间已满」 |
| 文档一致性 | 本页 vs 代码 | 函数名/签名与 §6 一致；DDL 与 `001_schema.sql` 逐字一致 |

## 10. 分支点与待拍板

| 编号 | 事项 | 选项 | 建议值 | 受哪项影响 |
| --- | --- | --- | --- | --- |
| B1 | 踢人后的 Token 失效方式 | Cloud：`revoke_token_ts` 立即失效 / 自建：短 TTL（5 分钟）+ 拒绝再签发 | 随 P3′ 定 | P3′ |
| B2 | 数据层连接与迁移 | 连接串形态、迁移工具（手写 SQL + `schema_migrations` / Alembic） | 手写 SQL + 版本表 | P9、P10 |
| B3 | 路由与会话中间件形态 | FastAPI `Depends` + Cookie / Bearer | FastAPI + Cookie（CORS + credentials） | P10、架构页 §7 |
| R-1 | 列表与详情的刷新策略 | 轮询 5s / 手动刷新 / SSE | 详情页轮询 5s（M3 起房内状态改走 LiveKit data channel） | 影响前端复杂度 |
| R-2 | 用邀请的落点 | ① 直接成为成员 ② 仍走等候室申请 | ②（与题面「进入房间前需经过等候室」一致） | 影响 M2 流程 |
| R-3 | 被踢过的人能否再申请 | 允许（记 `kicked` 历史）/ 设冷静期 | 允许 | 影响规则表 |
| R-4 | Host 移交 | 做（本文已给签名）/ 不做（Host 只能结束房间） | 做，归 M2 | 影响 M2 工作量 |

## What's next

1. 用户复核本页（重点：§4 规则表、§6 函数签名、§8 并发项、§10 分支点）。
2. 与 `docs/02-modules/r001-summaries.md`（纪要）、重写后的架构页、需求单一同转 `approved`。
3. 落实现：`cp-r001-1`（数据层）→ `cp-r001-2`（账户）→ `cp-r001-3`（房间与申请）→ `cp-r001-4`（页面与冒烟）。
