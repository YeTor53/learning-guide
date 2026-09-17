---
title: r001 应用架构与实现路径（M1 骨架 · 账户 · 房间）
description: M1 的架构、目录树、数据模型、权限矩阵、API 契约与逐文件函数级实现路径。
type: reference
status: superseded
owner: 陀梓皓
updated: 2026-09-16
---

<!-- overview -->
本轮怎么实现：技术栈、目录树、表结构、接口契约、每个文件里要写哪些函数（签名 + 职责 + 返回）。
需求与验收见 `docs/00-requirements/r001-skeleton-accounts-rooms.md`；方向与里程碑见 `docs/00-project/global-roadmap.md`。

> ⚠ **本页已作废（2026-09-16）**：用户拍板 **React 前端 + Python 后端 + PostgreSQL**，见 `docs/03-decisions/r001-adr-0002-stack-react-python-postgres.md`。本文的目录树、函数签名、会话方案、验证矩阵均需重写（生命周期 §4、API 信封 §5 的思路保留）；重写时机 = P9/P10/P3′ 拍板后一次完成。

## 1. 架构与运行拓扑（M1）

```
浏览器 ──HTTP──> Next.js 16 dev server (localhost:3000)
                     │  页面 (App Router, React Server/Client Components)
                     │  API Route Handlers (Node runtime)  ← 唯一写库入口
                     ▼
                src/server/*（业务逻辑，纯函数 + 显式 db 参数）
                     ▼
                src/db/*（node:sqlite 语句 + 手写 SQL）
                     ▼
                data/app.db（SQLite 单文件，WAL）
```

- 单进程、单仓、单命令启动；无外部服务依赖（LiveKit 在 M2 才进来，且为本机进程）。
- 分层规则：**路由处理器只做「解析输入 → 取当前用户 → 调 server 函数 → 转信封」**，不写业务逻辑；`src/server/*` 不碰 `next/*` 与 HTTP 对象，全部依赖通过参数传入，便于冒烟脚本直连与后续单测。
- 数据访问一律在 `src/db/*`；SQL 全写在 `.sql` 文件里，`src/db/*.ts` 只做参数绑定与结果映射。

## 2. 目录与文件清单

```
LearningGuide-LiveKit/
├─ package.json                 # scripts: dev / build / start / db:init / smoke / check / livekit:start(M2)
├─ tsconfig.json                # strict, paths: @/* -> src/*
├─ next.config.ts               # 仅设 serverExternalPackages 等必要项
├─ .env.example                 # 已存在，M1 增补 DATABASE_FILE / SESSION_SECRET
├─ data/                        # SQLite 文件目录（.gitignore 已屏蔽）
├─ scripts/
│   ├─ db-init.mjs              # CLI：--reset / --seed，打印各表行数
│   └─ smoke.mjs                # CLI：走真实 HTTP 的冒烟检查（M1 片段）
└─ src/
    ├─ lib/
    │   ├─ env.ts               # 环境变量读取与校验
    │   ├─ ids.ts               # id / 房间码生成
    │   ├─ password.ts          # scrypt 哈希与校验
    │   ├─ session.ts           # 会话签名、Cookie 读写、requireUser
    │   └─ errors.ts            # AppError、错误码、结果信封
    ├─ db/
    │   ├─ schema.sql           # 全部 DDL（7 张业务表 + 版本表）
    │   ├─ seed.sql             # 演示数据
    │   ├─ client.ts            # 打开/复用/关闭 SQLite 连接
    │   ├─ migrate.ts           # 执行 schema.sql（按版本表幂等）
    │   └─ queries.ts           # 所有语句的绑定函数（按表分组）
    ├─ server/
    │   ├─ auth.ts              # 注册 / 登录 / 查当前用户
    │   └─ rooms.ts             # 建房 / 列表 / 详情 / 申请 / 批准 / 离开 / 结束
    ├─ app/
    │   ├─ layout.tsx  page.tsx
    │   ├─ login/page.tsx  register/page.tsx
    │   ├─ rooms/page.tsx  rooms/new/page.tsx  rooms/[id]/page.tsx
    │   └─ api/
    │       ├─ auth/register/route.ts   auth/login/route.ts
    │       ├─ auth/logout/route.ts     auth/me/route.ts
    │       ├─ rooms/route.ts                       # GET 列表 / POST 建房
    │       ├─ rooms/[id]/route.ts                  # GET 详情
    │       ├─ rooms/[id]/join-requests/route.ts    # GET 申请列表 / POST 提申请
    │       ├─ rooms/[id]/leave/route.ts            # POST 离开
    │       ├─ rooms/[id]/end/route.ts              # POST 结束
    │       └─ join-requests/[id]/approve|reject/route.ts
    └─ components/
        ├─ nav-bar.tsx  room-card.tsx  room-form.tsx
        ├─ join-request-list.tsx  login-form.tsx  register-form.tsx
```

## 3. 数据模型（`src/db/schema.sql`，实现时逐字落库）

一次建好全部业务表：M1 只用到前 4 张，但 schema 一次到位，避免后面为加表引入迁移工具。

```sql
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id            TEXT PRIMARY KEY,
  email         TEXT NOT NULL UNIQUE COLLATE NOCASE,
  display_name  TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS rooms (
  id          TEXT PRIMARY KEY,
  host_id     TEXT NOT NULL REFERENCES users(id),
  topic       TEXT NOT NULL CHECK (topic IN ('epicureanism','math-biology','german-history','custom')),
  topic_label TEXT NOT NULL,
  title       TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  status      TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','ended')),
  capacity    INTEGER NOT NULL DEFAULT 8 CHECK (capacity BETWEEN 2 AND 8),
  room_code   TEXT NOT NULL UNIQUE,
  created_at  TEXT NOT NULL DEFAULT (datetime('now')),
  ended_at    TEXT
);

CREATE TABLE IF NOT EXISTS room_members (
  id          TEXT PRIMARY KEY,
  room_id     TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
  user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role        TEXT NOT NULL CHECK (role IN ('host','moderator','participant')),
  status      TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive')),
  exit_reason TEXT CHECK (exit_reason IN ('self_leave','kicked','room_ended')),
  joined_at   TEXT NOT NULL DEFAULT (datetime('now')),
  left_at     TEXT,
  CHECK ((status = 'active'   AND exit_reason IS NULL     AND left_at IS NULL)
      OR (status = 'inactive' AND exit_reason IS NOT NULL AND left_at IS NOT NULL))
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_room_members_active
  ON room_members(room_id, user_id) WHERE status = 'active';

CREATE TABLE IF NOT EXISTS join_requests (
  id         TEXT PRIMARY KEY,
  room_id    TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
  user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  status     TEXT NOT NULL DEFAULT 'pending'
             CHECK (status IN ('pending','approved','rejected','withdrawn','cancelled')),
  message    TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  decided_at TEXT,
  decided_by TEXT REFERENCES users(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_join_requests_pending
  ON join_requests(room_id, user_id) WHERE status = 'pending';

CREATE TABLE IF NOT EXISTS invites (
  id         TEXT PRIMARY KEY,
  room_id    TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
  code       TEXT NOT NULL UNIQUE,
  created_by TEXT NOT NULL REFERENCES users(id),
  expires_at TEXT NOT NULL,
  max_uses   INTEGER NOT NULL DEFAULT 8,
  used_count INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS chat_messages (
  id         TEXT PRIMARY KEY,
  room_id    TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
  user_id    TEXT NOT NULL REFERENCES users(id),
  body       TEXT NOT NULL,
  kind       TEXT NOT NULL DEFAULT 'chat' CHECK (kind IN ('chat','system')),
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_chat_messages_room_time
  ON chat_messages(room_id, created_at DESC);

CREATE TABLE IF NOT EXISTS session_summaries (
  id            TEXT PRIMARY KEY,
  room_id       TEXT NOT NULL UNIQUE REFERENCES rooms(id) ON DELETE CASCADE,
  status        TEXT NOT NULL DEFAULT 'ready' CHECK (status IN ('ready','failed')),
  content       TEXT NOT NULL DEFAULT '',
  model         TEXT,
  source_count  INTEGER NOT NULL DEFAULT 0,
  error_message TEXT,
  created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS schema_migrations (
  version    TEXT PRIMARY KEY,
  applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

**关系与设计要点**

| 关系 | 说明 |
| --- | --- |
| `users 1—N rooms` | `rooms.host_id`（房主） |
| `rooms 1—N room_members N—1 users` | 成员关系带 `role`、`status`(`active`/`inactive`) 与 `exit_reason`(`self_leave`/`kicked`/`room_ended`)；退出记录保留历史，部分唯一索引保证同一人同时只有一条活跃记录 |
| `rooms 1—N join_requests N—1 users` | 同一人对同一房间同时只允许一条 `pending`（部分唯一索引承担并发防重）；房间结束时未决申请转 `cancelled`（见 §4） |
| `rooms 1—N invites` | 邀请码限定房间 + 过期时间 + 使用上限（M2 用） |
| `rooms 1—N chat_messages` | 消息落库，按 (room_id, created_at DESC) 取最近 N 条（M3 用） |
| `rooms 1—1 session_summaries` | 一房一纪要（`UNIQUE(room_id)`），失败也留行并记 `error_message`（M4 用） |

## 4. 房间生命周期（存储态 + 派生相位）

### 4.1 状态定义

**存储态**（`rooms.status`，唯一事实源）：

| 值 | 含义 | 进入条件 | 终态 |
| --- | --- | --- | --- |
| `active` | 开放：可申请、可批准、可加入、可发消息、可邀请 | 建房成功即进入（建房与写 Host 成员在同一事务） | 否 |
| `ended` | 结束：只读（详情 / 历史消息 / 纪要仍可查），一切变更操作被拒 | 仅 Host 调 `endRoom` | **是**（不可重开，见 §4.6） |

**派生相位**（不落库，按需算出，避免双源）：

| 相位 | 计算方式 | 用途 |
| --- | --- | --- |
| `active.idle` | `status='active'` 且房内无人（LiveKit room 未创建或已空） | 列表显示「可加入」 |
| `active.in_session` | `status='active'` 且 LiveKit room 内至少 1 人 | 列表显示「讨论中 · N 人」 |
| `ended` | `status='ended'` | 列表显示「已结束」+ 纪要入口 |

M1 只用到存储态（`deriveRoomPhase` 返回 `active.idle | ended`）；`in_session` 依赖 LiveKit 在场信息，M2 补齐同一函数的实现，签名不变。

### 4.2 状态转移

```
房间      —建房—> active —endRoom(仅Host)—> ended（终态）
成员      active —leave(本人)—> inactive(self_leave)   |  M2: —kick—> inactive(kicked)
                                                    |  —房间结束—> inactive(room_ended)
申请      —提交—> pending —approve—> approved（同时生成 active 成员）
                        |—reject—> rejected
                        |—房间结束—> cancelled
```

| 转移 | 触发者 | 前置条件 | 副作用（同一事务） | 失败错误码 |
| --- | --- | --- | --- | --- |
| `— → active` | 任意登录用户 | 主题合法、标题 1–80 字、简介 ≤500 字 | 写 `rooms`（含 `room_code`）+ 写 `room_members(role='host', status='active')` | `VALIDATION` |
| `active → ended` | 仅 Host | `status='active'` | ① `rooms.status='ended'`、`ended_at=now`；② 全部 `status='active'` 成员 → `inactive`/`exit_reason='room_ended'`/`left_at=now`；③ 全部 `pending` 申请 → `status='cancelled'`、`decided_at=now`、`decided_by=NULL`（NULL 表示系统自动）；④ M2 追加：`RoomService.deleteRoom` 强制断开全部连接；⑤ M4 追加：触发纪要生成 | 非 Host → `FORBIDDEN`；已结束 → `ROOM_ENDED` |
| `— → pending` | 任意登录用户 | 房间 `active`、非活跃成员、无待批申请 | 写 `join_requests` | `ROOM_ENDED` / `ALREADY_MEMBER` / `ALREADY_PENDING` |
| `pending → approved` | Host / Moderator | 房间 `active`、申请仍为 `pending`、活跃成员数 < `capacity` | 写 `room_members(role='participant', status='active')` + 更新申请（`decided_by=actor`） | `FORBIDDEN` / `ROOM_ENDED` / `ALREADY_MEMBER` / `ROOM_FULL` / `CONFLICT` |
| `pending → rejected` | Host / Moderator | 房间 `active`、申请为 `pending` | 更新申请（`decided_by=actor`） | `FORBIDDEN` / `ROOM_ENDED` / `CONFLICT` |
| `pending → cancelled` | 系统（房间结束时） | — | 见 `active → ended` ③ | — |
| 成员 `active → inactive(self_leave)` | 本人 | 是活跃成员且 `role ≠ 'host'` | `exit_reason='self_leave'`、`left_at=now` | `NOT_MEMBER` / `HOST_CANNOT_LEAVE` / `ROOM_ENDED` |
| 成员 `active → inactive(kicked)` | Host / Moderator（M2） | 目标为活跃成员且非 Host | 同上，`exit_reason='kicked'`；M2 追加：调 LiveKit 移除参与者并强制断开 | `FORBIDDEN` |
| 成员 `active → inactive(room_ended)` | 系统（房间结束时） | — | 见 `active → ended` ② | — |
| 角色 `participant → moderator` | Host（M2） | 目标为活跃成员 | 更新 `role` | `FORBIDDEN` |
| Host 移交（M2，见 R6） | Host | 目标为活跃成员 | 原 Host 与新 Host 的 `role` 互换 | `FORBIDDEN` |

### 4.3 生命周期 × 能力矩阵

| 能力 | 未登录 | 非成员已登录 | Participant | Moderator | Host | 房间 `ended`（任何角色） |
| --- | --- | --- | --- | --- | --- | --- |
| 看列表 / 详情 / 历史消息 | ✅（只读） | ✅ | ✅ | ✅ | ✅ | ✅（只读 + 「已结束」标识） |
| 创建房间 | ❌ `UNAUTHORIZED` | ✅ | ✅ | ✅ | ✅ | —（与该房间无关） |
| 提交加入申请 | ❌ `UNAUTHORIZED` | ✅ | ❌ `ALREADY_MEMBER` | ❌ `ALREADY_MEMBER` | ❌ `ALREADY_MEMBER` | ❌ `ROOM_ENDED` |
| 看申请列表 | ❌ `UNAUTHORIZED` | ❌ `FORBIDDEN` | ❌ `FORBIDDEN` | ✅ | ✅ | ✅（只读，供追溯） |
| 批准 / 拒绝申请 | ❌ `UNAUTHORIZED` | ❌ `FORBIDDEN` | ❌ `FORBIDDEN` | ✅ | ✅ | ❌ `ROOM_ENDED` |
| 离开房间 | ❌ `UNAUTHORIZED` | ❌ `NOT_MEMBER` | ✅ | ✅ | ❌ `HOST_CANNOT_LEAVE` | ❌（已是 `inactive`） |
| 结束房间 | ❌ `UNAUTHORIZED` | ❌ `FORBIDDEN` | ❌ `FORBIDDEN` | ❌ `FORBIDDEN` | ✅ | ❌ `ROOM_ENDED` |
| 查看纪要 | ❌ `UNAUTHORIZED` | ✅ | ✅ | ✅ | ✅ | ✅（M4；生成在结束流程内，失败可重试） |
| 踢人（M2） | ❌ `UNAUTHORIZED` | ❌ `FORBIDDEN` | ❌ `FORBIDDEN` | ✅ | ✅ | ❌ `ROOM_ENDED` |

### 4.4 结束房间的实现约束

- **单入口**：`endRoom` 是唯一能把房间置为 `ended` 的函数；M2 的「踢最后一人」「Host 掉线」「全员离开」都**不得**隐式结束房间。
- **事务边界**：§4.2 中 `active → ended` 的 ①②③ 必须在同一个 SQLite 事务内完成，失败整体回滚——不允许出现「房间已 ended 但成员仍 active」或「成员已 inactive 但房间仍 active」。
- **外部副作用的顺序（M2/M4）**：先提交数据库事务，再调 LiveKit `deleteRoom` 与纪要生成；外部调用失败只记日志与状态（纪要置 `status='failed'` + `error_message`），**不回滚**房间结束——房间结束是用户意图，不应被外部服务可用性阻塞。
- **幂等**：重复调 `endRoom` 返回 409 `ROOM_ENDED`，不产生二次副作用；纪要靠 `session_summaries.UNIQUE(room_id)` 防重。

### 4.5 生命周期 × 其它表

| 表 | 房间结束时 | 结束后的可见性 |
| --- | --- | --- |
| `room_members` | 活跃行 → `inactive(room_ended)` | 详情页展示历史成员与退出原因 |
| `join_requests` | `pending` → `cancelled` | Host/Moderator 仍可查看，作审计线索 |
| `invites` | 不删不改；校验时统一要求房间 `active` | 邀请链接自然失效（提示「房间已结束」） |
| `chat_messages` | 全部保留（纪要输入 + 追溯） | 详情页只读展示 |
| `session_summaries` | 触发一次生成（M4），`UNIQUE(room_id)` 防重 | 详情页可查看；失败行保留 `error_message` |

### 4.6 明确不做（生命周期边界）

- **不自动结束**：房间空置不触发结束，必须 Host 显式结束（本轮保持行为可预测，不做定时空房回收）。
- **不可重开**：`ended` 是终态，不提供 `reopen`；同一主题要再讨论就新建房间（避免消息与纪要历史被改写）。
- **不删除房间**：不提供删除接口；`ended` 房间保留只读可查。
- **不做定时邀请清理**：过期邀请不移除行，靠 `expires_at` 与房间状态共同判定。

## 5. API 契约

结果信封（所有接口统一）：

```json
{ "ok": true,  "data": { ... } }
{ "ok": false, "error": { "code": "ROOM_FULL", "message": "房间已满（上限 8 人）" } }
```

| 方法 | 路径 | 权限 | 请求体 / 查询 | 成功 | 错误码 |
| --- | --- | --- | --- | --- | --- |
| POST | `/api/auth/register` | 公开 | `{email, displayName, password}` | 201 `{user}` + 会话 Cookie | `VALIDATION`、`EMAIL_TAKEN` |
| POST | `/api/auth/login` | 公开 | `{email, password}` | 200 `{user}` + Cookie | `INVALID_CREDENTIALS` |
| POST | `/api/auth/logout` | 登录 | — | 200 `{}`（清 Cookie） | `UNAUTHORIZED` |
| GET | `/api/auth/me` | 公开 | — | 200 `{user}` 或 `{user:null}` | — |
| GET | `/api/rooms` | 公开 | `?status=active|ended|all&topic=&mine=1` | 200 `{rooms:[RoomListItem]}` | `VALIDATION` |
| POST | `/api/rooms` | 登录 | `{topic, topicLabel, title, description}` | 201 `{room, membership}` | `VALIDATION` |
| GET | `/api/rooms/:id` | 公开 | — | 200 `RoomDetail` | `NOT_FOUND` |
| POST | `/api/rooms/:id/join-requests` | 登录 | `{message?}` | 201 `{request}` | `NOT_FOUND`、`ROOM_ENDED`、`ALREADY_MEMBER`、`ALREADY_PENDING` |
| GET | `/api/rooms/:id/join-requests` | Host/Moderator | `?status=pending` | 200 `{requests}` | `FORBIDDEN` |
| POST | `/api/join-requests/:id/approve` | Host/Moderator | — | 200 `{request, member}` | `FORBIDDEN`、`ROOM_ENDED`、`ROOM_FULL`、`ALREADY_MEMBER`、`CONFLICT`（申请已非 pending） |
| POST | `/api/join-requests/:id/reject` | Host/Moderator | — | 200 `{request}` | `FORBIDDEN` |
| POST | `/api/rooms/:id/leave` | 登录成员 | — | 200 `{}`（成员转 `inactive/self_leave`） | `NOT_MEMBER`、`HOST_CANNOT_LEAVE`、`ROOM_ENDED` |
| POST | `/api/rooms/:id/end` | Host | — | 200 `{room}` | `FORBIDDEN`、`ROOM_ENDED` |

视图对象（服务端裁剪后返回，不直接吐库行）：

```ts
type UserVO         = { id: string; email: string; displayName: string; createdAt: string }
type RoomVO         = { id: string; topic: string; topicLabel: string; title: string; description: string;
                        status: 'active'|'ended'; capacity: number; roomCode: string;
                        host: { id: string; displayName: string }; createdAt: string; endedAt: string|null }
type RoomListItem   = RoomVO & { memberCount: number; pendingCount: number; myRole: Role|null; myRequest: 'pending'|'approved'|'rejected'|null }
type RoomDetail     = RoomListItem & { members: MemberVO[]; recentMessages: MessageVO[] }
type MemberVO       = { userId: string; displayName: string; role: Role; joinedAt: string;
                        status: 'active'|'inactive'; exitReason: 'self_leave'|'kicked'|'room_ended'|null }
type JoinRequestVO  = { id: string; roomId: string; user: { id: string; displayName: string };
                        status: 'pending'|'approved'|'rejected'|'withdrawn'|'cancelled'; message: string;
                        createdAt: string; decidedAt: string|null; decidedBy: string|null }
```

## 6. 逐文件函数级实现路径（M1）

签名即契约；`VO` 见 §5。

### 6.1 `src/lib/env.ts`

| 函数 | 签名 | 职责 / 返回 |
| --- | --- | --- |
| `requireEnv` | `(name: string): string` | 读环境变量，空值抛 `AppError('CONFIG_MISSING')`；仅此函数读 `process.env` |
| `env`（导出常量） | `{ databaseFile: string; sessionSecret: string; roomCapacity: number; llmBaseUrl: string; llmApiKey: string; llmModel: string }` | 启动期一次性解析；LLM 三项 M1 可空 |

### 6.2 `src/lib/errors.ts`

| 函数 | 签名 | 职责 / 返回 |
| --- | --- | --- |
| `AppError` | `class extends Error { code: ErrCode; status: number }` | 业务错误载体，构造 `(code, message, status=400)` |
| `appError` | `(code: ErrCode, message?: string, status?: number): AppError` | 简写构造器 |
| `jsonOk` | `<T>(data: T, status = 200): Response` | 输出 `{ok:true,data}` |
| `jsonError` | `(e: unknown): Response` | `AppError` → 状态码 + 错误信封；其他 → 500 `INTERNAL`（日志打完整栈，响应不回显内部信息） |

错误码清单：`VALIDATION 400`、`UNAUTHORIZED 401`、`INVALID_CREDENTIALS 401`、`FORBIDDEN 403`、`NOT_FOUND 404`、`NOT_MEMBER 409`、`EMAIL_TAKEN 409`、`ALREADY_MEMBER 409`、`ALREADY_PENDING 409`、`ROOM_ENDED 409`、`ROOM_FULL 409`、`HOST_CANNOT_LEAVE 409`、`CONFIG_MISSING 500`、`INTERNAL 500`。

### 6.3 `src/lib/ids.ts`

| 函数 | 签名 | 职责 / 返回 |
| --- | --- | --- |
| `newId` | `(prefix: string): string` | `usr_`/`room_`/`mem_`/`req_` + base32url(10 字节随机) |
| `newRoomCode` | `(): string` | 6 位大写字母数字，剔除 `0O1I`，用于房间码/邀请码 |

### 6.4 `src/lib/password.ts`

| 函数 | 签名 | 职责 / 返回 |
| --- | --- | --- |
| `hashPassword` | `async (plain: string): Promise<string>` | scrypt(16 字节盐, N=16384,r=8,p=1)，输出 `scrypt$16384$8$1$<saltB64>$<hashB64>` |
| `verifyPassword` | `async (plain: string, stored: string): Promise<boolean>` | 解析存储串重算并用 `timingSafeEqual` 比对；格式非法返回 false |

### 6.5 `src/lib/session.ts`

| 函数 | 签名 | 职责 / 返回 |
| --- | --- | --- |
| `signSession` | `(payload: {userId: string; exp: number}, secret: string): string` | `base64url(JSON).base64url(HMAC-SHA256)` |
| `readSession` | `(token: string, secret: string): {userId: string; exp: number} \| null` | 验签 + 过期校验，任何异常返回 null |
| `setSessionCookie` | `async (userId: string): Promise<void>` | 写 `lg_session`：HttpOnly、SameSite=Lax、Path=/、`maxAge` 7 天、生产加 Secure |
| `clearSessionCookie` | `async (): Promise<void>` | 清 Cookie |
| `getCurrentUser` | `async (): Promise<UserVO \| null>` | 读 Cookie → 验签 → 查库取用户 |
| `requireUser` | `async (): Promise<UserVO>` | 未登录抛 `UNAUTHORIZED 401` |

### 6.6 `src/db/client.ts` · `migrate.ts`

| 函数 | 签名 | 职责 / 返回 |
| --- | --- | --- |
| `openDb` | `(file: string): DatabaseSync` | 打开/建目录、`PRAGMA journal_mode=WAL`、`foreign_keys=ON`、`busy_timeout=3000` |
| `getDb` | `(): DatabaseSync` | 进程内单例（`globalThis` 缓存，避免 dev 热重载重复打开） |
| `closeDb` | `(): void` | 关闭连接（CLI / 冒烟脚本用） |
| `runMigrations` | `(db: DatabaseSync): { applied: string[] }` | 读 `schema.sql` 逐句执行；以 `schema_migrations` 记版本 `r001-base`，已存在则跳过 |
| `resetDatabase` | `(db: DatabaseSync): void` | 删全部业务表（仅 `--reset` 显式调用） |
| `seedDatabase` | `(db: DatabaseSync): { users: number; rooms: number; messages: number }` | 执行 `seed.sql`（幂等写法：`INSERT OR IGNORE` 固定 id），返回写入行数 |

### 6.7 `src/db/queries.ts`（按表分组，全部返回库行类型）

| 函数 | 签名 | 职责 / 返回 |
| --- | --- | --- |
| `insertUser` | `(db, row: UserRow): void` | 写 users |
| `findUserByEmail` | `(db, email: string): UserRow \| undefined` | 登录查重（COLLATE NOCASE 已由 schema 保证） |
| `findUserById` | `(db, id: string): UserRow \| undefined` | 会话取用户 |
| `insertRoom` | `(db, row: RoomRow): void` | 写 rooms |
| `findRoomById` | `(db, id: string): RoomRow \| undefined` | 房间详情/校验 |
| `updateRoomStatus` | `(db, id: string, status: 'active'\|'ended', endedAt: string \| null): void` | 结束房间 |
| `listRooms` | `(db, f: {status?: string; topic?: string; hostId?: string}): RoomRow[]` | 列表（含 ended） |
| `insertMember` | `(db, row: MemberRow): void` | 写成员（host 建房时 / 批准时） |
| `findActiveMember` | `(db, roomId: string, userId: string): MemberRow \| undefined` | 权限判定 |
| `countActiveMembers` | `(db, roomId: string): number` | 成员数（M2 上限校验、列表展示） |
| `markMemberInactive` | `(db, roomId: string, userId: string, reason: 'self_leave'\|'kicked'\|'room_ended', at: string): void` | 置 `status='inactive'`、`exit_reason`、`left_at`（`room_ended` 走批量路径） |
| `listMembers` | `(db, roomId: string, opts?: {includeInactive?: boolean}): MemberRow[]` | 详情页成员列表（默认只活跃；`includeInactive` 用于已结束房间的历史展示） |
| `insertJoinRequest` | `(db, row: JoinRequestRow): void` | 写申请（唯一索引兜底防重） |
| `findJoinRequestById` | `(db, id: string): JoinRequestRow \| undefined` | 批准/拒绝 |
| `findPendingRequest` | `(db, roomId: string, userId: string): JoinRequestRow \| undefined` | 重复提交判定 |
| `listJoinRequests` | `(db, roomId: string, status?: string): JoinRequestRow[]` | 申请列表 |
| `decideJoinRequest` | `(db, id: string, status: 'approved'\|'rejected', decidedBy: string, decidedAt: string): void` | 落决定 |
| `closeRoomGraph` | `(db, roomId: string, at: string): {membersClosed: number; requestsCancelled: number}` | 结束房间的连带写入：成员批量 `inactive(room_ended)` + `pending` 申请批量 `cancelled`（单条 SQL 各自的批量 UPDATE，供 `endRoom` 事务调用） |
| `countPendingRequests` | `(db, roomId: string): number` | 列表徽标 |
| `listRecentMessages` | `(db, roomId: string, limit: number): MessageRow[]` | 详情页历史消息（M3 复用） |

### 6.8 `src/server/auth.ts`

| 函数 | 签名 | 职责 / 返回 |
| --- | --- | --- |
| `registerUser` | `async (db, input: {email: string; displayName: string; password: string}): Promise<UserVO>` | 规范化 email/昵称 → 校验（email 格式、昵称 1–32 字、密码 ≥8 位）→ 查重（冲突抛 `EMAIL_TAKEN`）→ 哈希 → `insertUser` → 返回 VO |
| `authenticate` | `async (db, input: {email: string; password: string}): Promise<UserVO>` | 查库 + `verifyPassword`；失败统一抛 `INVALID_CREDENTIALS`（不区分账号不存在/密码错误） |
| `getUserById` | `(db, id: string): UserVO \| null` | 会话恢复用 |

### 6.9 `src/server/rooms.ts`

| 函数 | 签名 | 职责 / 返回 |
| --- | --- | --- |
| `createRoom` | `(db, actor: UserVO, input: {topic: string; topicLabel: string; title: string; description?: string}): RoomVO & {myRole: Role}` | 事务：校验主题/标题 → `insertRoom`（room_code 冲突重试 3 次）→ `insertMember(role='host')` → 返回房间 + 我的角色 |
| `listRooms` | `(db, actor: UserVO \| null, filter: {status?: 'active'\|'ended'\|'all'; topic?: string; mine?: boolean}): RoomListItem[]` | 查房间 + 聚合成员数/待批数 + 我的角色与我的申请状态 |
| `getRoomDetail` | `(db, actor: UserVO \| null, roomId: string): RoomDetail` | 房间 + 成员列表（按角色、加入时间排序）+ 最近 20 条消息；不存在抛 `NOT_FOUND` |
| `requestJoin` | `(db, actor: UserVO, roomId: string, message?: string): JoinRequestVO` | 校验：房间存在且 `active`（否则 `ROOM_ENDED`）、非活跃成员（否则 `ALREADY_MEMBER`）、无 pending（否则 `ALREADY_PENDING`）→ 写申请 |
| `listJoinRequests` | `(db, actor: UserVO, roomId: string, status?: string): JoinRequestVO[]` | 先 `assertRoomRole(db, actor, roomId, ['host','moderator'])` |
| `approveJoinRequest` | `(db, actor: UserVO, requestId: string): {request: JoinRequestVO; member: MemberVO}` | 事务：`assertRoomRole` → **房间须 `active`**（否则 `ROOM_ENDED`）→ 申请须为 `pending`（否则 `ALREADY_MEMBER`/`CONFLICT`）→ 活跃成员数 `< capacity`（否则 `ROOM_FULL`）→ `insertMember(role='participant')` + `decideJoinRequest('approved')` |
| `rejectJoinRequest` | `(db, actor: UserVO, requestId: string): JoinRequestVO` | `assertRoomRole` → `decideJoinRequest('rejected')` |
| `leaveRoom` | `(db, actor: UserVO, roomId: string): void` | 房间须 `active`（否则 `ROOM_ENDED`）→ 活跃成员存在否则 `NOT_MEMBER` → `role='host'` 抛 `HOST_CANNOT_LEAVE` → `markMemberInactive(..., 'self_leave', now)` |
| `endRoom` | `(db, actor: UserVO, roomId: string): RoomVO` | `assertRoomRole(db, actor, roomId, ['host'])`；已结束抛 `ROOM_ENDED`；**单事务**执行 `updateRoomStatus('ended', now)` + `closeRoomGraph(db, roomId, now)`（见 §4.2/§4.4，M2 起在事务提交后追加 `deleteRoom`，M4 追加纪要生成） |
| `deriveRoomPhase` | `(db, roomId: string): 'active.idle'\|'active.in_session'\|'ended'` | 派生相位（不落库）：M1 只区分 `active.idle` / `ended`；M2 接 LiveKit 在场信息补 `in_session` |
| `assertRoomActive`（内部） | `(db, roomId: string): RoomRow` | 房间存在（否则 `NOT_FOUND`）且 `status='active'`（否则 `ROOM_ENDED`）；所有变更型函数的第一步 |
| `assertRoomRole`（内部） | `(db, actor: UserVO \| null, roomId: string, allowed: Role[]): MemberRow` | 未登录 `UNAUTHORIZED`；非活跃成员 `FORBIDDEN`；角色不符 `FORBIDDEN` |

### 6.10 路由处理器（薄壳，每个文件 5~15 行）

| 文件 | 函数 | 行为 |
| --- | --- | --- |
| `api/auth/register/route.ts` | `POST(req)` | 解析 JSON → `registerUser` → `setSessionCookie` → `jsonOk(user, 201)` |
| `api/auth/login/route.ts` | `POST(req)` | `authenticate` → `setSessionCookie` → `jsonOk(user)` |
| `api/auth/logout/route.ts` | `POST()` | `requireUser` → `clearSessionCookie` → `jsonOk({})` |
| `api/auth/me/route.ts` | `GET()` | `getCurrentUser` → `jsonOk({ user })` |
| `api/rooms/route.ts` | `GET(req)` / `POST(req)` | 列表用 `listRooms(actor?, filter)`；建房 `requireUser` → `createRoom` |
| `api/rooms/[id]/route.ts` | `GET(_req, {params})` | `getRoomDetail(actor?, id)` |
| `api/rooms/[id]/join-requests/route.ts` | `GET` / `POST` | `listJoinRequests` / `requestJoin` |
| `api/rooms/[id]/leave/route.ts` | `POST` | `leaveRoom` |
| `api/rooms/[id]/end/route.ts` | `POST` | `endRoom` |
| `api/join-requests/[id]/approve/route.ts` | `POST` | `approveJoinRequest` |
| `api/join-requests/[id]/reject/route.ts` | `POST` | `rejectJoinRequest` |

所有 route 文件顶部统一 `export const runtime = 'nodejs'`（SQLite 需要 Node runtime，不能用 Edge）。

### 6.11 页面与组件

| 文件 | 函数/组件 | 职责 |
| --- | --- | --- |
| `app/layout.tsx` | `RootLayout` | 全局壳 + `NavBar`（显示当前用户/登录登出） |
| `app/page.tsx` | `HomePage` | 服务端组件：直接调 `listRooms` 渲染 + 指引 |
| `app/login/page.tsx` / `register/page.tsx` | `LoginPage` / `RegisterPage` | 表单；提交打 `/api/auth/*`，成功后 `router.push('/rooms')` |
| `app/rooms/page.tsx` | `RoomsPage` | 服务端组件：房间列表（主题筛选、状态筛选、成员数、我的角色） |
| `app/rooms/new/page.tsx` | `NewRoomPage` | 建房表单（主题下拉 + 标题 + 简介）；未登录重定向 `/login?next=/rooms/new` |
| `app/rooms/[id]/page.tsx` | `RoomDetailPage` | 房间详情：信息、成员、待批申请（Host/Moderator 可见批准/拒绝按钮）、最近消息、申请/离开/结束按钮 |
| `components/nav-bar.tsx` | `NavBar` | 登录态导航 |
| `components/room-card.tsx` | `RoomCard` | 列表项卡片 |
| `components/room-form.tsx` | `RoomForm` | 建房表单（客户端） |
| `components/join-request-list.tsx` | `JoinRequestList` | 申请列表 + 批准/拒绝操作 |
| `components/login-form.tsx` / `register-form.tsx` | `LoginForm` / `RegisterForm` | 表单客户端逻辑与错误提示 |

页面取数规则：M1 的页面统一用**服务端组件直接调 `src/server/*`**（同一进程、同一 SQLite 连接），不再绕一层 HTTP；只有需要交互的提交动作走 `/api/*`。好处：少一半代码、避免 M1 就陷入 fetch 编排。

### 6.12 `scripts/db-init.mjs` · `scripts/smoke.mjs`

| 脚本 | 行为 |
| --- | --- |
| `db-init.mjs` | 解析 `--reset` / `--seed` → `getDb()` → `resetDatabase?` → `runMigrations` → `seedDatabase?` → 打印每张表行数（真实输出，作为验收证据） |
| `smoke.mjs` | 顺序执行：`POST /api/auth/register`（随机邮箱）→ 校验 201 → 登录另一账号 → 建房 → `GET /api/rooms` 校验含新房间 → `POST join-requests` → `GET join-requests` → `POST approve` → 校验成员数 2 → `POST leave` → 打印每步 `状态码 + 关键字段`，任一步不符即非 0 退出 |

冒烟前需 dev server 已起：脚本先探测 `http://localhost:3000/api/auth/me`，未通则提示「请先 `npm run dev`」并退出。

## 7. 认证与会话设计

- **存储**：`users.password_hash` 用 scrypt 加盐；不存明文、不存可逆串。
- **会话**：自签 HMAC Cookie（`lg_session`），格式 `base64url(JSON).base64url(HMAC-SHA256)`，payload 只含 `userId` 与 `exp`（7 天）。
  - 选它的理由：零外部依赖、逻辑 30 行、评审可读；代价：无服务端会话吊销（登出靠清 Cookie）——在设计说明「安全与取舍」中如实写明。
  - 备选（R2）：引入 `jose`/`next-auth`，多一个依赖但换来成熟实现与轮换能力。
- **Cookie 属性**：HttpOnly、SameSite=Lax、Path=/；生产环境补 Secure。
- **密钥**：`SESSION_SECRET` 仅存 `.env`；`.env.example` 留占位；缺失时 `requireEnv` 直接失败（不静默用默认值）。
- **输入校验**：所有入口在 `src/server/*` 内校验类型/长度，路由处理器不信任前端。

## 8. 失败与边界情况（本轮覆盖）

| 情况 | 期望行为 |
| --- | --- |
| 未登录调受保护接口 | 401 `UNAUTHORIZED`，不泄露资源是否存在 |
| 重复注册同邮箱 | 409 `EMAIL_TAKEN` |
| 登录密码错误 / 邮箱不存在 | 统一 401 `INVALID_CREDENTIALS` |
| 对已结束房间提交申请 | 409 `ROOM_ENDED` |
| 已是成员再提交申请 | 409 `ALREADY_MEMBER` |
| 同人重复提交待批申请 | 409 `ALREADY_PENDING`（并靠部分唯一索引兜底并发） |
| 普通成员调批准接口 | 403 `FORBIDDEN` |
| Host 想离开自己的房间 | 409 `HOST_CANNOT_LEAVE`（提示先结束房间） |
| 房间不存在 / id 非法 | 404 `NOT_FOUND` |
| 建房标题为空或超长 | 400 `VALIDATION`（标题 1–80 字、简介 ≤500 字） |
| 数据库文件目录不存在 | `openDb` 自动创建 `data/` |
| 同一房间被两人同时批准导致并发写 | 事务 + 部分唯一索引；冲突时返回 409 而非 500 |
| 已结束房间：申请 / 批准 / 离开 / 再次结束 | 一律 409 `ROOM_ENDED`（列表、详情、历史消息、纪要仍可只读） |
| 结束房间时数据库事务失败 | 整体回滚，房间保持 `active`；不出现「房间已结束但成员仍 active」的半状态 |
| 结束后重复结束 | 409 `ROOM_ENDED`，且不重复触发纪要生成 |
| 结束房间时外部服务（LiveKit / LLM）失败 | 房间结束照常生效（事务已提交）；失败只记日志与 `session_summaries.status='failed'`，可在详情页重试 |

## 9. 验证矩阵（M1）

| 层 | 命令 / 操作 | 判据 |
| --- | --- | --- |
| 类型 | `npx tsc --noEmit` | 无错误 |
| 数据 | `node scripts/db-init.mjs --reset --seed` | 打印 7 张表行数，`users≥3`、`rooms≥3`、`chat_messages≥6` |
| 接口 | `node scripts/smoke.mjs` | 每步状态码符合预期，末尾打印 `PASS n/n` |
| 人工 | 双浏览器：A 建房 → B 申请 → A 批准 → B 详情页看到自己的成员身份 | 页面数据与库一致 |
| 安全 | `git grep -n "API_SECRET" src/` | 无命中（`.env.example` 除外） |
| 文档 | 对照本页与需求单 | 文件清单与函数签名一致、验收清单已勾 |

## 10. 待验证技术假设（实现前先跑最小探针）

1. `node:sqlite` 在 Next 16 route handler（`runtime='nodejs'`）内可用 → cp1 探针；不可用则换 `better-sqlite3` 并更新本页。
2. `@next/swc-win32-x64-msvc` 能从 npmmirror 取到（Next 16 装包）→ cp1 实测；失败切官方 registry（临时，不改仓库配置）。
3. Next 16 的 `cookies()` 为异步 API → 在 `session.ts` 内统一 `await`。
4. React 19 与 `@livekit/components-react` 2.9.24 兼容 → M2 实测（本轮不装 LiveKit 依赖）。

## 11. 待拍板项（R1~R5）

| 编号 | 事项 | 选项 | 建议值 | 影响 |
| --- | --- | --- | --- | --- |
| R1 | P5/P6 最终拍板 | A/A（本文档假设）/ 改 B 或 C | A/A | 改则本文整体重写 |
| R2 | 会话实现 | 自签 HMAC Cookie（零依赖）/ `jose` / `next-auth` | 自签 HMAC | 影响安全叙事与代码量 |
| R3 | `invites` 表与邀请 API 时机 | 表随 r001 建、API 归 M2（本文假设）/ M1 一起做完 | 表随 r001 建、API 归 M2 | 影响 r001 工作量与 M2 起点 |
| R4 | 建表策略 | 一次建全部 7 表（本文假设）/ 只建 M1 用到的表、后续加迁移 | 一次建全部 | 影响后续是否要写迁移脚本 |
| R5 | 冒烟脚本形态 | 走真实 HTTP（本文假设，贴题面「集成测试」）/ 直连 `src/server/*`（快但偏单测） | 走真实 HTTP | 影响 `smoke.mjs` 与启动依赖 |
| R6 | Host 退出方式 | ① 禁止 Host 离开，必须先结束房间（本文假设）② 增加「移交 Host」后可离开（M2 实现 `transferHost`） | ① | 影响「房主换人继续开会」是否可用；② 多一个函数 + 页面入口 |
| R7 | 房间结束时未决申请 | 置 `cancelled` 并记 `decided_at`（本文假设）/ 保持 `pending` 不动 | `cancelled` | 影响已结束房间申请列表的语义与审计 |

## 12. What's next

1. 用户复核本文（R1~R5 一并拍板）。
2. 本文与需求单 `status: draft → approved`。
3. 建 `req/r001-skeleton` 分支，按 cp-r001-1（骨架与数据层）→ cp-r001-2（账户）→ cp-r001-3（房间与申请）→ cp-r001-4（页面与冒烟）推进，每 cp 一提交一 tag。
