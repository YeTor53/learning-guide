---
title: r001 房间功能详细设计（模块页）
description: 房间的生命周期、业务规则、PostgreSQL 数据模型、接口、后端与前端函数级实现路径、并发边界与验证。
type: reference
status: approved
owner: 陀梓皓
updated: 2026-09-17
---

<!-- overview -->
本页是**房间功能**的单一事实源：领域规则、数据模型、接口、逐文件函数级实现路径、并发与边界、验证矩阵。
不在本页重复的：结果信封与后端目录总览（以重写后的 `docs/01-architecture/r001-app-architecture.md` 为准）、项目方向与里程碑（`docs/00-project/global-roadmap.md`）、纪要（M4，归档页 `docs/99-archive/r001-ahead-m4-summaries.md`）。
本文对三项待拍板保持中立，只在 §10 标出分支点：LiveKit 来源（P3′）、PostgreSQL 落地（P9）、后端框架与迁移工具（P10）。

> 功能行为、交互状态、按钮与提示文案以 **功能页** `docs/02-modules/r001-rooms-features.md` 为准；本页只讲怎么实现（数据模型 / 接口 / 函数路径）。
> **范围**：本文只覆盖 r001（M1）；邀请/踢人/角色/移交等 M2 内容已移至 `docs/99-archive/r001-ahead-m2-m3-rooms.md`（`status: backlog`）。

## 1. 范围与里程碑归属

| 项 | 里程碑 | 本文是否给到实现级 |
| --- | --- | --- |
| 建房（主题/标题/简介）、列表、详情 | M1 | ✅ |
| 加入申请：提交 / 列表 / 批准 / 拒绝 | M1 | ✅ |
| 离开房间、结束房间（含连带动作） | M1 | ✅ |
| 入房环节「房间已满」提示、音视频/屏幕共享/举手/焦点（LiveKit 能力） | M2/M3 | 不在本文（见各自能力页） |
| 房间码与邀请（限时链接）、踢人、角色任命、Host 移交 | M2 | **已移出本文** → `docs/99-archive/r001-ahead-m2-m3-rooms.md` |
| 文字群聊实时收发 | M3 | 本文只保留「详情页只读展示最近 20 条」（表与读路径）；写入与实时收发属 M3 |

明确不做：房间删除、重开已结束房间、房间自动结束、公网部署、多租户。

## 2. 领域模型

**存储态（`rooms.status`，唯一事实源）**：`active`（开放）→ `ended`（终态）。

**派生相位（不落库）**：`active.idle`（房内无人）、`active.in_session`（房内 ≥1 人）、`ended`。
- M1：`derive_room_phase` 只区分 `active.idle` / `ended`。
- M2：接 LiveKit 在场信息补 `in_session`（函数签名不变）。

**实体关系**：`users 1—N rooms`（host）；`rooms 1—N room_members N—1 users`；`rooms 1—N join_requests N—1 users`；`rooms 1—N invites`；`rooms 1—N chat_messages`；`rooms 1—1 session_summaries`。

**成员退出语义（单源）**：`room_members.status ∈ {active, inactive}` + `exit_reason ∈ {self_leave, kicked, room_ended}`，并用 CHECK 强制两者一致（`active` 必须无 `exit_reason`/`left_at`，`inactive` 必须两者都有）。

## 3. 数据模型（PostgreSQL）

> `session_summaries`（纪要表）属 M4，定义见归档页 `docs/99-archive/r001-ahead-m4-summaries.md` §3（单一事实源，不在此复制）。

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
| 列表 | 任何人 | `status` ∈ {active,ended,all}；`topic` 可选；`mine=1` 需登录（口径：我建的 / 我参与过的 / 我有待批申请的） | 只读；聚合 `member_count`/`pending_count`/`my_role`/`my_request`；**`pending_count` 只对房主/协管返回真值，其余一律 0**（FQ-4） | `VALIDATION` |
| 详情 | 任何人 | 房间存在 | 只读；房间 + 活跃成员 + 最近 20 条消息 + 我的状态 | `NOT_FOUND` |
| 提交申请 | 登录用户 | 房间 `active`；非活跃成员；无 `pending` | 写 `join_requests(pending)` | `ROOM_ENDED` / `ALREADY_MEMBER` / `ALREADY_PENDING` |
| 看申请列表 | Host/Moderator | 房间存在 | 只读（`status` 可选过滤） | `FORBIDDEN` |
| 批准 | Host/Moderator | 房间 `active`；申请 `pending`；活跃人数 < `capacity` | **锁 `rooms` 行** → 写成员 `participant/active` + 申请置 `approved`（`decided_by=actor`） | `FORBIDDEN` / `ROOM_ENDED` / `ROOM_FULL` / `ALREADY_MEMBER` / `CONFLICT` |
| 拒绝 | Host/Moderator | 房间 `active`；申请 `pending` | 申请置 `rejected`（`decided_by=actor`） | `FORBIDDEN` / `ROOM_ENDED` / `CONFLICT` |
| 撤回申请 | **申请人本人** | 申请 `pending`；锁 `rooms` 行 | 申请置 `withdrawn`（`decided_by=本人`）；撤回后可立即再申请 | `FORBIDDEN` / `CONFLICT` |
| 离开 | 本人（非 Host） | 房间 `active`；是活跃成员 | 成员置 `inactive/self_leave` + `left_at` | `NOT_MEMBER` / `HOST_CANNOT_LEAVE` / `ROOM_ENDED` |
| 结束房间 | **仅 Host** | 房间 `active` | **锁 `rooms` 行**：① `status=ended`、`ended_at`；② 全部活跃成员 → `inactive/room_ended`；③ 全部 `pending` 申请 → `cancelled`（`decided_by=NULL` 表示系统）；④ 提交后（M2）：`delete_room` 强制断开；⑤ 提交后（M4）：触发纪要生成 | `FORBIDDEN` / `ROOM_ENDED` |

角色权限矩阵与生命周期转移细节沿用已确认口径（三个角色 × `active`/`ended` 两态），已在 `global-roadmap.md` §2 与本文 §4 表内完全覆盖，不再另开一节复制。

## 5. 接口清单（本模块）

信封 `{ok, data}` / `{ok, error:{code,message}}` 与错误码总表见架构页；本模块路径：

| 方法 | 路径 | 权限 | 请求 | 成功 |
| --- | --- | --- | --- | --- |
| GET | `/api/rooms` | 公开 | `?status=active\|ended\|all&topic=&mine=1&limit=20&offset=0` | 200 `{rooms: RoomListItem[], total, limit, offset}`；`pendingCount` 对非管理者恒为 0 |
| POST | `/api/rooms` | 登录 | `{topic, topicLabel, title, description?}` | 201 `RoomVO & {myRole}` |
| GET | `/api/rooms/{room_id}` | 公开 | — | 200 `RoomDetail` |
| POST | `/api/rooms/{room_id}/join-requests` | 登录 | `{message?}` | 201 `JoinRequestVO` |
| GET | `/api/rooms/{room_id}/join-requests` | Host/Moderator | `?status=pending` | 200 `{requests: JoinRequestVO[]}` |
| POST | `/api/join-requests/{request_id}/approve` | Host/Moderator | — | 200 `{request, member}` |
| POST | `/api/join-requests/{request_id}/reject` | Host/Moderator | — | 200 `{request}` |
| POST | `/api/join-requests/{request_id}/withdraw` | 申请人本人 | — | 200 `{request}` |
| POST | `/api/rooms/{room_id}/leave` | 活跃成员 | — | 200 `{}` |
| POST | `/api/rooms/{room_id}/end` | Host | — | 200 `RoomVO` |

## 6. 后端实现路径（逐文件：函数签名 + 职责 + 返回）

```
backend/
├─ app/db/sql/001_schema.sql          # §3 的 DDL（逐字）
├─ app/db/sql/002_seed.sql            # 演示账号 3 个、示例房间 3 个、历史消息 12 条、1 个已结束房间（纪要属 M4，本轮无该表）
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
| `my_active_roles` | `(conn, user_id: str, room_ids: list[str]) -> dict[str, str]` | 批量取我在这些房间的活跃角色（列表 `my_role` 用，cp-r001-3 新增） |
| `my_pending_requests` | `(conn, user_id: str, room_ids: list[str]) -> set[str]` | 批量取我有待批申请的房间 id（列表 `my_request_status` 用，cp-r001-3 新增） |
| `update_room_ended` | `(conn, room_id: str, at: datetime) -> None` | `status='ended', ended_at=%s` |
| `insert_member` | `(conn, row: NewMember) -> None` | 写活跃成员 |
| `get_active_member` | `(conn, room_id: str, user_id: str) -> MemberRow \| None` | 权限判定 |
| `count_active_members` | `(conn, room_id: str) -> int` | 上限与展示 |
| `list_members` | `(conn, room_id: str, include_inactive: bool = False) -> list[MemberRow]` | 成员列表（历史含 `exit_reason`） |
| `deactivate_member` | `(conn, room_id: str, user_id: str, reason: str, at: datetime) -> None` | 单成员退出 |
| `deactivate_all_members` | `(conn, room_id: str, at: datetime) -> int` | 房间结束时批量 `room_ended`；返回受影响行数 |
| `insert_join_request` | `(conn, row: NewJoinRequest) -> None` | 写申请（部分唯一索引兜底并发） |
| `get_join_request` | `(conn, request_id: str) -> JoinRequestRow \| None` | 批准/拒绝 |
| `get_pending_request` | `(conn, room_id: str, user_id: str) -> JoinRequestRow \| None` | 重复申请判定 |
| `list_join_requests` | `(conn, room_id: str, status: str \| None) -> list[JoinRequestRow]` | 申请列表 |
| `decide_join_request` | `(conn, request_id: str, status: str, decided_by: str \| None, at: datetime) -> None` | 落决定（`decided_by=None` 表示系统） |
| `cancel_pending_requests` | `(conn, room_id: str, at: datetime) -> int` | 房间结束时批量 `cancelled`；返回行数 |
| `withdraw_join_request` | `(conn, request_id: str, at: datetime, by: str) -> None` | 申请人撤回 → `withdrawn` + `decided_at` + `decided_by=本人` |
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
| `withdraw_join_request` | `(conn, actor: User, request_id: str) -> JoinRequestVO` | 仅本人；`lock_room` → 申请 `pending` → 置 `withdrawn`（撤回后可立即再申请） |
| `leave_room` | `(conn, actor: User, room_id: str) -> None` | `lock_room` → `active` → 活跃成员 → 非 Host → `deactivate_member(self_leave)` |
| `end_room` | `(conn, actor: User, room_id: str) -> RoomVO` | `lock_room` → `assert_room_role(host)` → `active` → `update_room_ended` + `deactivate_all_members` + `cancel_pending_requests`（同事务）→ 提交后副作用（M2 `delete_room`、M4 纪要） |
| `assert_room_active`（内部） | `(room: RoomRow \| None) -> RoomRow` | 存在否则 `NOT_FOUND`；`active` 否则 `ROOM_ENDED` |
| `assert_room_role`（内部） | `(conn, actor: User \| None, room_id: str, allowed: Sequence[str]) -> MemberRow` | 未登录 `UNAUTHORIZED`；非活跃成员 `FORBIDDEN`；角色不符 `FORBIDDEN` |
| `assert_manager_role`（内部） | `(conn, actor: User \| None, room: RoomRow) -> None` | 申请列表可见性：活跃 host/moderator 放行；**房间已结束时**放行房主与历史协管（追溯查看，功能页 F-05） |

事务约定：`create_room / approve_join_request / reject_join_request / leave_room / end_room / kick_member / set_member_role / transfer_host / redeem_invite` 全部在**单个事务**内完成（service 内 `with conn.transaction():`）；只读函数不显式开事务。

> 本页不设 §6.5：原 §6.5 `app/services/livekit.py` 属 M2，已随邀请/踢人一起移出 → `docs/99-archive/r001-ahead-m2-m3-rooms.md` §6.5。

### 6.6 `app/schemas/rooms.py`（Pydantic v2）

| 模型 | 字段 | 说明 |
| --- | --- | --- |
| `CreateRoomIn` | `topic: Literal[...]`, `topic_label: str`, `title: str`, `description: str = ""` | 长度约束与 §4 一致 |
| `JoinRequestIn` | `message: str = ""` | ≤200 字 |
| `UserVO` / `MemberVO` / `RoomVO` / `RoomListItem` / `RoomDetail` / `JoinRequestVO` / `InviteVO` | 见架构页字段表 | 出参只暴露 VO，不吐库行 |

### 6.7 `app/api/routers/rooms.py` + `app/api/deps.py`

| 文件 | 函数 | 职责 |
| --- | --- | --- |
| `deps.py` | `current_user_optional()`, `current_user()` | 从会话 Cookie 解析用户（会话方案已定：签名 Cookie + HttpOnly/SameSite=Lax，见架构页 §6） |
| `deps.py` | `db_conn()` | 每请求一个连接（`with get_conn() as conn: yield conn`） |

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
| Host 想离开 | `HOST_CANNOT_LEAVE`，提示「先结束房间或移交 Host」（移交见 R-4） |
| 重复结束房间 | 锁内检查 `status='active'` → `ROOM_ENDED`；不触发二次副作用（纪要 `UNIQUE(room_id)` 防重） |
| 数据库连接中断 | 连接池在借出前检测失效连接；`OperationalError` 映射 `INTERNAL` 并在响应中不回显 DSN |
| 长文本与注入 | 描述/消息长度由 CHECK 与 Pydantic 双重约束；SQL 全参数化，禁止字符串拼 SQL |

## 9. 验证矩阵

| 层 | 对象 | 判据 |
| --- | --- | --- |
| 迁移 | `python backend/scripts/db_init.py --reset --seed` | 打印 7 张表行数：`schema_migrations=2`、`users≥3`、`rooms≥3`、`room_members≥6`、`join_requests≥3`、`chat_messages≥12`、`invites` 本轮为空（0，表先建、M2 才用） |
| 单元/集成（pytest） | `tests/test_rooms_service.py` | 建房写 Host 成员（1 条 `active`）；重复申请→`ALREADY_PENDING`；`capacity` 满→`ROOM_FULL`（塞 8 人后第 9 个被拒）；`end_room` 后成员全 `inactive/room_ended`、`pending` 全 `cancelled`；非 Host `end_room`→`FORBIDDEN`；`HOST_CANNOT_LEAVE`；已结束房间 `request_join`→`ROOM_ENDED` |
| 并发 | `tests/test_rooms_concurrency.py` | 两个线程同时批准最后一个名额：恰好 1 个成功、1 个 `ROOM_FULL`，库中活跃成员数 = `capacity` |
| 冒烟（真实 HTTP） | `python scripts/smoke.py` | 每步状态码符合预期，末尾打印 `PASS n/n` |
| 手工演示 | 两个浏览器 | A 建房 → B 申请 → A 批准 → B 详情见自己为成员；房间满 8 人时第 9 人提示「房间已满」 |
| 文档一致性 | 本页 vs 代码 | 函数名/签名与 §6 一致；DDL 与 `001_schema.sql` 逐字一致 |

## 10. 分支点与待拍板

| 编号 | 事项 | 选项 | 建议值 | 受哪项影响 |
| --- | --- | --- | --- | --- |
| B2 | 数据层连接与迁移 | 已定：`psycopg` 连接池 + 手写 SQL + `schema_migrations` 版本表（ADR-0005 / 架构页 §7） | — | 已闭环 |
| B3 | 路由与会话中间件形态 | 已定：FastAPI `Depends` + 签名 Cookie；开发与交付均走同源（Vite 代理 / 静态托管），不放开 CORS | — | 已闭环（架构页 §6） |
| R-1 | 列表与详情的刷新策略 | 轮询 5s / 手动刷新 / SSE | 详情页轮询 5s（M3 起房内状态改走 LiveKit data channel） | 影响前端复杂度 |

## 11. 变更记录

| 日期 | 轮次 | 变更 | 原因 |
| --- | --- | --- | --- |
| 2026-09-17 | r001 | §9 迁移判据由「`session_summaries≥1`」改为 r001 实际 7 张表行数；命令补 `backend/` 前缀 | 纪要表属 M4，r001 不建该表，原判据无法满足 |
| 2026-09-17 | r001 | §6 目录注释去掉种子里的「纪要」；补注 §6.5 已移出本页 | 同上（避免读者以为 r001 会写纪要数据） |
| 2026-09-17 | r001 | §6.3 补 `my_active_roles` / `my_pending_requests`；§6.4 补 `assert_manager_role` | cp-r001-3 实现中为「避免列表 N+1」与「结束后可追溯查看申请」新增，签名已落地 |
| 2026-09-17 | r001 | §4 补「撤回申请」规则、§5 补第 10 条路由 `/api/join-requests/{id}/withdraw`、§6.3/§6.4 补对应函数 | 功能页 F-04 的「撤回申请」按钮此前在接口清单里缺对应端点（设计漏项），补齐后行为与文案一致 |
| 2026-09-17 | r001 | §4/§5 标注 `pending_count` 的可见性：非房主/协管服务端返回 0 | 用户 2026-09-17 拍板「严格返回 0」（对应功能页 FQ-4），不再只靠前端隐藏 |
| 2026-09-17 | r001 | §4 列表行的 `mine=1` 口径写实：我建的 / 我参与过的 / 我有待批申请的 | 功能页 F-01 的「我参与」在实现中含「有待批申请」，卡片「已申请」徽标需要它 |

## What's next

1. 用户复核本页（重点：§4 规则表、§6 函数签名、§8 并发项、§10 分支点）。
2. 与重写后的架构页、需求单一同转 `approved`（纪要/邀请/踢人等非本轮内容已在 `docs/99-archive/`）。
3. 落实现：`cp-r001-1`（数据层）→ `cp-r001-2`（账户）→ `cp-r001-3`（房间与申请）→ `cp-r001-4`（页面与冒烟）。
