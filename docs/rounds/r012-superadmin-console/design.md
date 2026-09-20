---
title: r012 设计：超管用户 · 简单管理后台 · 全服大屏聊天（逐文件函数级）
description: 迁移 011 数据模型、超管隐身进房与旁路权限收敛、管理后台三列表与三动作、全服大屏聊天与 SSE 通知通道的函数级设计；含契约面清单、教学契约、失败与边界、回退方案与视觉契约。
type: design
status: draft
owner: 陀梓皓
updated: 2026-09-20
---

<!-- overview -->
行号基准：本页写于 r011 `ab8edb5`（cp-7）；此后已把 r011 收尾两个提交（cp-8 响应延迟收敛 / cp-8b 台账）**merge 进本分支**（merge 提交 `e0c6598`，基点 = r011 HEAD `24b0bad`）。cp-8 只动前端 hook/页面与项目级文档，**后端行号不变**；`main` = `96b1153`。以下行号均为**改动前**的实际位置（`git grep -n` 实测），实现时以 `git diff` 为准。
本页只写**改哪个文件的哪个函数、签名与职责是什么、依据来自哪条验收**；不改规范、不引入新依赖（SSE 用原生 `EventSource` + FastAPI `StreamingResponse`）。
待拍板项见需求单 §10（`ASK-r012-1`，Q1~Q18）；本页按**建议值**展开，凡受某题影响的小节都在标题后标 `[Qn]`，改选项只影响标了它的小节。

## 0. 本轮定性（L 级别，就高不就低）

| 组 | 项 | 级别 | 依据 |
| --- | --- | --- | --- |
| A | 超管身份 + 隐身进房 + 旁路治理 | **L3** | Q1/Q2 数据模型变（`users.role`、新表 `room_visits`）、Q3 对外可见面变（成员列表/舞台/名册行为）、Q5 边界变（权限面新增一类角色）；Q4/Q8 补充：**超管不发布音视频**（Token 关发布权限，界面无设备控件） |
| B | 管理后台（三列表 + 三动作 + 审计） | **L3** | Q1 新表 `admin_audit`、新增对外端点族 `/admin/*`、Q5 能力面新增 |
| C | 全服大屏聊天 + SSE 通道 | **L3** | 新表 `global_messages`、新增对外端点与**新传输形态**（`text/event-stream`），是既有无 SSE/WS 架构（ADR-0013：DataChannel 只加速、HTTP 是唯一真相）的一处新增，须 ADR-0025 定口径 |
| D | 在线口径（`users.last_seen_at`） | **L3** | Q14=2 定案：**新增对外端点 `POST /api/presence`** + 前端 60 秒心跳，故由 L2 升为 L3（对外可见面新增） |

三条 L3 都要出 ADR（ADR-0024 / ADR-0025）并在实现期按 2.0 闸门走；若实现中发现设计不成立，先停手取证再定级。

## 1. 数据模型：迁移 `011_r012_superadmin_global_chat.sql` [Q1][Q2][Q7][Q13][Q14][Q16]

新增文件 `backend/app/db/sql/011_r012_superadmin_global_chat.sql`（前进式迁移，ADR-0005；`db_init.py --reset` 可重建）：

```sql
-- 011_r012_superadmin_global_chat.sql — r012：超管身份 / 在册旁路 / 全服聊天 / 审计
-- 设计事实源：docs/rounds/r012-superadmin-console/design.md §1；改动须同步 docs/02-modules/r012-superadmin-console.md

-- Q1①：超管身份落在 users（单列，零新表）
ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'user'
  CHECK (role IN ('user','superadmin'));
-- Q14②：在线口径 = 前端每 60 秒 POST /api/presence 写入的最近一次心跳时间（判据窗口见 §2.6）
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS ix_users_last_seen ON users (last_seen_at DESC);

-- Q2①：超管不写 room_members；进出记旁路表（天然隐身、天然不占人数）
CREATE TABLE IF NOT EXISTS room_visits (
  id         TEXT PRIMARY KEY,
  room_id    TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
  user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  entered_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  left_at    TIMESTAMPTZ,
  hidden     BOOLEAN NOT NULL DEFAULT true
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_room_visits_open
  ON room_visits (room_id, user_id) WHERE left_at IS NULL;

-- C 组：全服大屏聊天（不复用 room_id NOT NULL 的 chat_messages）
CREATE TABLE IF NOT EXISTS global_messages (
  id         TEXT PRIMARY KEY,
  user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  body       TEXT NOT NULL CHECK (char_length(body) BETWEEN 1 AND 500),
  created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS ix_global_messages_time ON global_messages (created_at DESC);
-- 限流走库计数（重启不放大额度）：按 (user_id, created_at) 建索引
CREATE INDEX IF NOT EXISTS ix_global_messages_user_time ON global_messages (user_id, created_at DESC);

-- Q7①：管理动作审计（**故意不 FK 到 rooms**：删房后流水仍在，target_id 允许悬空——见 §8）
CREATE TABLE IF NOT EXISTS admin_audit (
  id          TEXT PRIMARY KEY,
  actor_id    TEXT REFERENCES users(id) ON DELETE SET NULL,
  action      TEXT NOT NULL,
  target_type TEXT NOT NULL CHECK (target_type IN ('room','user','summary')),
  target_id   TEXT NOT NULL,
  detail      JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS ix_admin_audit_time ON admin_audit (created_at DESC);
```

要点：
- **删除房间的级联**已由既有 FK 承担（实测：`room_members` / `join_requests` / `invites` / `chat_messages` / `room_hand_raises` / `room_focus` / `session_summaries` / `focus_requests` / `transcripts` 全部 `ON DELETE CASCADE`），所以删房只需 `DELETE FROM rooms WHERE id = %s`；`room_visits` 与 `global_messages` 亦为 CASCADE / 独立。
- **容量口径（ADR-0016）不变**：`count_active_members` 只数 `room_members`，超管不写该表 → 「在册 ≤ 容量」不变量自动成立（这正是 Q2 选① 的理由；要写进 ADR-0024）。
- `admin_audit.detail` 用 JSONB 存前后值摘要（例 `{"before":{"status":"active"},"after":{"status":"ended"}}`）。

## 2. A 组：超管身份与隐身进房（后端）[Q1][Q2][Q3][Q4][Q6][Q8]

### 2.1 `backend/app/services/roles.py`（**新增**，最小角色工具）

```python
SUPERADMIN = "superadmin"

def is_superadmin(actor: Optional[UserVO]) -> bool:
    """超管判据的唯一入口（其它模块禁止直接比较字符串 role）。"""

def assert_superadmin(actor: Optional[UserVO]) -> UserVO:
    """未登录 → 401 UNAUTHORIZED；非超管 → 403 FORBIDDEN（管理后台全部端点用它）。"""
```

### 2.2 旁路校验的**收敛点**（改 2 个函数，所有调用点自动受益）[Q6]

现状实测：权限地基是两个函数——`services/rooms.py::assert_room_role`（:201，踢人/改角色/移交/结束都调它）与 `assert_manager_role`（:224，看待批申请/纪要可见性）。设计只在**这两处**加超管旁路，而不是散改 20 多个调用点：

```python
# backend/app/services/rooms.py
def _virtual_admin_member(actor: UserVO, room_id: str) -> MemberRow:
    """超管的**虚拟成员行**：只用于让既有调用点读到 role='host'，**永不写库**（docstring 与 ADR-0024 双处声明）。"""

def assert_room_role(conn, actor, room_id, allowed) -> MemberRow:
    """（改）超管旁路：actor 为超管且房间存在 → 返回 _virtual_admin_member(actor, room_id)；
    房间不存在仍 404（不因超管身份凭空造房）。其余逻辑与文案不变。"""

def assert_manager_role(conn, actor, room) -> None:
    """（改）超管旁路：actor 为超管且房间存在 → 直接 return（待批申请可见、纪要可生成）。"""

def effective_role(conn, actor, room_id) -> Optional[str]:
    """（新）对外视角的「我的身份」：超管 → 'superadmin'；否则 repo.get_active_member 的 role（含 None）。
    list_rooms / get_room_detail 用它填 `myRole`，前端据此显示管理入口与治理按钮。"""
```

改动点（既有行号）：`list_rooms`:286 的 `repo.my_active_roles` 结果、`get_room_detail`:311 的 `my_role` 组装改用 `effective_role`；`_visible_pending_count`:115 增加 `my_role in (*MANAGER_ROLES, SUPERADMIN)`（超管看得到待批数）。

**不受影响、必须显式确认的**：`services/messages.py::_guard_active_member`（:28，房内发言/看消息要活跃成员）—— 超管按 Q4① **不在房间聊天栏发言**（只在大屏发言），所以**不**给它开口子；若 Q4 改成 ②/③，此处要另立例外并重评 L3。

### 2.3 取票：超管免成员校验 + 隐身 + 不占人数 [Q2][Q3][Q8]

`services/rooms.py::issue_room_token`（:526）新增超管分支（其余分支与顺序不动）：

```python
def issue_room_token(conn, actor, room_id) -> RoomTokenVO:
    """（改）拦截顺序后插入：actor 为超管 →
       ① 房间不存在 404 / 已结束 409 与现逻辑一致（超管也不能进已结束房间的实时层——历史内容走只读接口）；
       ② 跳过「活跃成员」校验（不查 room_members）；
       ③ repo.insert_room_visit(...)（已有未关闭访问记录则复用，不重复插）；
       ④ livekit_service.issue_token(..., hidden=True, attributes={"lg-role": "superadmin"},
                                    can_publish=False, can_publish_data=False)；   # Q4/Q8 补充：只管理、不出声不出画
       ⑤ 返回体与普通成员**完全一致**（Token/url/roomName/expiresIn），前端无需分叉。"""
```

`services/livekit.py::issue_token`（:29）签名扩展（**只加可选参数，保持向后兼容**）：

```python
def issue_token(room_name, user_id, display_name, role, settings=None,
                ttl_seconds=None, max_participants=None, *,
                hidden: bool = False, attributes: Optional[dict[str, str]] = None) -> str:
    """（改）新增只读参数：hidden / attributes / can_publish（默认 None=沿用现值 True，**不动普通成员行为**）。
    超管取票固定传 hidden=True + attributes={"lg-role":"superadmin"} + can_publish=False + can_publish_data=False
    —— 理由（你 2026-09-20 原话）：音频视频走 LiveKit 计费，为省额度，超管不能说话和视频，只能管理。
    实测依据：livekit-api 1.2.1 的 VideoGrants 含 `hidden` 字段（注释原文「participant is not visible to
    other participants」）与 `can_publish` / `can_publish_data`、AccessToken 含 `with_attributes`
    （`site-packages/livekit/api/access_token.py`）。超管的 room_admin 仍为 False（最小权限：管理能力一律走我方 HTTP）。"""
```

新仓储函数（`backend/app/repositories/rooms.py`，紧邻 `count_active_members`:316）：

```python
def insert_room_visit(conn, row: NewRoomVisit) -> None            # 插一条 hidden=true 的访问记录
def close_room_visit(conn, room_id, user_id, at) -> None          # 离开时补 left_at（幂等：仅更新未关闭行）
def list_open_visits(conn, room_id) -> list[RoomVisitRow]         # 房里还挂着哪些超管（后台「在场超管」列用）
```
配合：`services/rooms.py::leave_room`（:485）与 `end_room`（:499）内补 `close_room_visit`（超管离开/房间结束时收口）。

### 2.4 隐身的三道拦线（缺一即"隐身失败"）

| # | 拦线 | 位置 | 做法 |
| --- | --- | --- | --- |
| 0 | **发布面**（Q4/Q8 补充） | Token grants | `can_publish=False` + `can_publish_data=False` → 超管**发不出**音视频与数据；前端也不渲染麦克风/摄像头控件（双保险，见 §5 `RoomLivePage`） |
| 1 | LiveKit 参与者面 | Token grants | `hidden=True`（实测字段存在）；实现第一步就用 **2 浏览器真机**验证「另一端的 participants / 舞台 / 名册看不到超管」 |
| 2 | 本库成员面 | 不写 `room_members` | 成员列表（`GET /rooms/{id}` / 抽屉成员 tab）、人数、待批可见性天然不含超管 |
| 3 | 转写 worker | `backend/agents/transcriber.py::TranscriberPool._maybe_start`（:237） | 在既有 `pid.startswith("agent-")` 判据旁补 `or (participant.attributes or {}).get("lg-role") == "superadmin"` → 跳过（**双保险**：hidden 已可能让 worker 看不见他） |

前端侧还有第 4 道（**仅本端自见**）：超管自己的那一格不进舞台、控制坞显示「隐身中」（见 §5）。E10 的取证 = worker 日志无该 identity 的「开转写会话」+ 纪要素材无其文本。

### 2.5 超管账号从哪来 [Q15]

- `backend/scripts/grant_superadmin.py`（**新增**）：`python backend/scripts/grant_superadmin.py --email <邮箱> [--revoke]`；打印「邮箱 / 改前角色 → 改后角色 / 影响行数」；缺邮箱或查不到用户 → 退出码 2 并打印原因（零副作用）。
- `backend/scripts/db_init.py`（**改**）：seed 段增一个演示超管账号（`role='superadmin'`），口令与既有演示账号同源；重复初始化幂等。
- `backend/app/repositories/users.py`（**改**）：`_COLUMNS`（:14）补 `role, last_seen_at`；`UserRow`（:18）补两字段；`insert_user`（:30）加 `role: str = "user"`；新增 `touch_last_seen(conn, user_id, at)`、`set_user_role(conn, user_id, role)`。

### 2.6 在线口径（前端短轮询心跳）[Q14=2]

你 2026-09-20 定案：**不用「请求即心跳」**，改由前端按固定周期上报。设计如下：

- **新端点** `POST /api/presence`（`api/routers/presence.py`，登录必需、无请求体）：`cur = Depends(current_user)` → `presence.touch(conn, cur.id)` → `200 {"ok": true, "lastSeenAt": ...}`。手写不碰任何房间/成员逻辑，幂等。
- **新服务** `backend/app/services/presence.py`：

```python
def touch(conn, user_id: str, *, now: Optional[datetime] = None) -> datetime
    """把 users.last_seen_at 写成当前时间并返回它（**每次上报都写**，不做内存节流——周期由前端控制）。"""
def is_online(last_seen_at: Optional[datetime], *, now: Optional[datetime] = None) -> bool
    """在线 = now - last_seen_at ≤ settings.presence_online_seconds。"""
def online_user_ids(conn) -> set[str]
    """大屏面板「在线」判据（Q13=1 的在线点用）；一次 SQL 取回集合。"""
```
- **前端** `frontend/src/hooks/usePresenceBeat.ts`：`PRESENCE_BEAT_MS = 60_000`（单点可调）；`setInterval` 触发，**仅当** `document.visibilityState === 'visible'` 且已登录时才真发（沿用 `useRosterSync` 的可见性判据，不空跑请求）；登录成功后立刻补一次，`beforeunload` 不特殊处理（离线靠超时自然收敛）。挂在 `App.tsx` 顶层（一次挂载，全站生效）。新 api 模块 `frontend/src/api/presence.ts`（`presenceApi.beat()`）。
- **判据窗口 `presence_online_seconds` 默认 120**（= 2× 轮询周期，容一次丢包不掉线）；要严格「60 秒内算在线」→ 改这一个数（`config.py::Settings` + `.env.example`）。
- **不再改动** `api/deps.py`：请求链路上不写库（避免每个请求一次 UPDATE）。

## 3. B 组：简单管理后台（后端）[Q5][Q6][Q7][Q16]

### 3.1 `backend/app/repositories/admin.py`（**新增**）

```python
class AdminRoomFilter(NamedTuple):     # status: Optional[str]; q: Optional[str]; limit: int; offset: int
class AdminUserFilter(NamedTuple):     # q: Optional[str]; online_only: bool; limit: int; offset: int
class AdminSummaryFilter(NamedTuple):  # status: Optional[str]; limit: int; offset: int
class AdminAuditFilter(NamedTuple):    # action: Optional[str]; limit: int; offset: int
class AdminRoomRow / AdminUserRow / AdminSummaryRow / AdminAuditRow   # 行 dataclass（含跨表拼接字段）
class NewAudit(NamedTuple):            # id, actor_id, action, target_type, target_id, detail(dict), created_at

def list_rooms_page(conn, f) -> tuple[list[AdminRoomRow], int]
    """房间 + 房主显示名 + 在册人数 + 待批数 + 纪要状态/字数；一次 JOIN 出全，避免 N+1（对齐 repo.room_aggregates 的既有做法）。"""
def list_users_page(conn, f) -> tuple[list[AdminUserRow], int]
    """用户 + 参与房间数 + 发言数 + 转写条数 + last_seen_at；online_only 用 last_seen_at 判据。"""
def list_summaries_page(conn, f) -> tuple[list[AdminSummaryRow], int]
    """纪要 + 房间标题/主题 + status + provider/model + 字数（char_length）。"""
def list_audit_page(conn, f) -> tuple[list[AdminAuditRow], int]
def insert_audit(conn, row: NewAudit) -> None
def delete_room(conn, room_id: str) -> int        # DELETE FROM rooms WHERE id=%s（级联靠 FK），返回影响行数
def room_exists(conn, room_id: str) -> bool
```

### 3.2 `backend/app/services/admin.py`（**新增**）

```python
ADMIN_ACTIONS = ("room.end", "room.delete", "room.summary_regenerate")   # 审计 action 词表（单点）

def _audit(conn, actor, action, target_type, target_id, detail) -> None
    """统一写审计（id 用 security/ids.new_id('audit')）。与业务动作同一个事务，保证「有动作必有流水」。"""
def list_rooms(conn, actor, f) -> tuple[list[AdminRoomItem], int]        # 每个都先 assert_superadmin(actor)
def list_users(conn, actor, f) -> tuple[list[AdminUserItem], int]
def list_summaries(conn, actor, f) -> tuple[list[AdminSummaryItem], int]
def list_audit(conn, actor, f) -> tuple[list[AdminAuditItem], int]
def end_room(conn, actor, room_id) -> RoomVO
    """超管结束任意房间：**直接复用** rooms_service.end_room(conn, actor, room_id)（其内部的 assert_room_role
    已被 §2.2 旁路放行）→ 事务内补 _audit(...) ；外部 LiveKit 调用仍由 end_room 在提交后执行（ADR-0011 条 4）。"""
def delete_room(conn, actor, room_id) -> None
    """Q16① 硬删除：不存在 404 → 事务内 { 取快照（标题/房主/人数/消息数）→ _audit → repo.delete_room }；
    提交后 livekit_service.delete_room(room_id)（失败不回滚，日志如实记）；返回 200 + { deleted: true }。"""
def regenerate_summary(conn, actor, room_id) -> SessionSummaryVO
    """超管生成/重生纪要：复用 summary_service.generate_summary(conn, actor, room_id)（其 assert_manager_role
    已旁路）；成功后 _audit；LLM 未配置/失败的错误语义与现口径一致（503 / 502）。"""
```

### 3.3 路由 `backend/app/api/routers/admin.py`（**新增**，`prefix="/api"` 由 `main.register_routers` 加）

| 方法 | 路径 | 出参 | 依据 |
| --- | --- | --- | --- |
| GET | `/admin/rooms?status=&q=&limit=&offset=` | `{ items, total, limit, offset }` | E5 |
| GET | `/admin/users?q=&onlineOnly=&limit=&offset=` | 同上 | E5 |
| GET | `/admin/summaries?status=&limit=&offset=` | 同上 | E5 |
| GET | `/admin/audit?action=&limit=&offset=`（Q7① 才做） | 同上 | E6 |
| POST | `/admin/rooms/{room_id}/end` | `RoomVO` | E6 |
| DELETE | `/admin/rooms/{room_id}` | `{ deleted: true }` | E6 |
| POST | `/admin/rooms/{room_id}/summary` | `SessionSummaryVO` | E6 |

鉴权统一走新依赖 `backend/app/api/deps.py::current_superadmin`（= `current_user` + `roles.assert_superadmin`），**每个端点都依赖它**（不靠前端隐藏入口）。分页沿用 `schemas/common.py::LimitOffset`（默认 20 / 上限 100）。

## 4. C 组：全服大屏聊天 + SSE（后端）[Q11][Q13][Q14]

### 4.1 `backend/app/repositories/global_chat.py`（**新增**）

```python
GLOBAL_BODY_MAX = 500
def insert_global_message(conn, row: NewGlobalMessage) -> None
def list_global_messages(conn, limit: int, before_id: Optional[str]) -> list[GlobalMessageRowWithName]
    """倒序取最近 N 条（与 chat_messages 列表同风格：JOIN users 取显示名），before_id 做游标分页。"""
def count_recent_by_user(conn, user_id: str, since: datetime) -> int   # 限流：窗口内已发条数（库计数）
```

### 4.2 `backend/app/services/global_chat.py`（**新增**）

```python
def _vo(row: GlobalMessageRowWithName) -> GlobalMessageVO          # 含 authorName / createdAt / onlineOnline 标
def list_messages(conn, actor: Optional[UserVO], *, limit: int, before_id: Optional[str]) -> list[GlobalMessageVO]
    """**未登录也能看**（Q4①：大屏是公开面）；不校验成员身份，不走 room 任何逻辑。"""
def post_message(conn, actor: UserVO, body: str) -> GlobalMessageVO
    """登录才能发（未登录 → 401）。顺序：① 长度 1..500（Pydantic 与 DB CHECK 双保险）
    ② 限流：count_recent_by_user(now - window) ≥ GLOBAL_CHAT_RATE_LIMIT → 429 RATE_LIMITED
    ③ 落库（唯一真相）④ 提交后 events.publish("global_message", {"id": ...})（只推最小载荷）
    """
def online_marks(conn) -> set[str]        # 配合 Q13：列表里给每条的作者打「当前在线」标
```
新增配置（`config.py`，单点可调）：`global_chat_rate_limit: int = 5`、`global_chat_rate_window_seconds: int = 10`、`global_chat_page_default: int = 50`。

### 4.3 `backend/app/services/events.py`（**新增**，进程内 pub/sub）

```python
class Subscriber:                      # queue: asyncio.Queue[dict]; close()/closed 属性
def subscribe() -> Subscriber          # 超过 settings.sse_max_subscribers（默认 200）→ 抛 AppError 503（不回 500）
def unsubscribe(sub: Subscriber) -> None
def publish(event_type: str, payload: dict) -> None
    """同步、非阻塞：每个订阅者 put_nowait；队列满（settings.sse_subscriber_queue_max，默认 32）→ 丢最旧 + 记日志。"""
def subscriber_count() -> int
def next_event_id() -> int             # 进程内单调递增（SSE 的 `id:` 用它，支撑断线续传语义）
```
**已知限制（写进 ADR-0025 与 review）**：进程内内存态，多进程/多机部署会漏事件；前端靠重连 + 轮询兜底，功能不丢。

### 4.4 路由 `backend/app/api/routers/global_chat.py` / `events.py`（**新增**）

| 方法 | 路径 | 权限 | 出参 |
| --- | --- | --- | --- |
| GET | `/global-messages?limit=&beforeId=` | 任意（含未登录） | `{ items, total?, limit }` |
| POST | `/global-messages` | 登录 | `GlobalMessageVO`（超限 429 `RATE_LIMITED`） |
| GET | `/events` | 任意（含未登录） | `text/event-stream` |

**SSE 协议（一次写死，前后端共用一份口径）**：

```
GET /api/events            Accept: text/event-stream
响应头：Content-Type: text/event-stream; charset=utf-8
        Cache-Control: no-cache, no-store
        Connection: keep-alive
        X-Accel-Buffering: no            # 防反代缓冲（本机 uvicorn 直连无影响，公网部署时有用）

id: 41
event: notify
data: {"type":"global_message","payload":{"id":"gmsg_01J..."}}

: ping                                # 每 settings.sse_keepalive_seconds（默认 15）秒一行注释，保活不触发 onmessage
```

- **只推通知型事件**：`type ∈ {global_message, room_changed, admin_action}`，`payload` 只带 id 等最小载荷；前端收到后**照旧走 HTTP 拉真相**（沿用 ADR-0013「HTTP 落库是唯一真相」）。
- 事件名固定用 `notify`（不用多 event 名，避免前端漏解）；`retry: 3000` 首帧给出重连间隔。
- 实现：`async def stream_events(...)` → `StreamingResponse(gen(), media_type="text/event-stream", headers={...})`；`gen()` 内 `while True: try: ev = await asyncio.wait_for(sub.queue.get(), timeout=keepalive) except TimeoutError: yield ": ping\n\n"`；客户端断开（`await request.is_disconnected()`）或异常 → `finally: events.unsubscribe(sub)`。
- 登录态：`Depends(current_user_optional)`（未登录也能收公屏事件）；不需要 `user` 也可以建立连接。

## 5. 前端逐文件（block A/B/C 的用户可见面）

| 文件 | 动作 | 内容 |
| --- | --- | --- |
| `frontend/src/api/auth.ts` | 改 | `User` 类型补 `role: string`（`/me`、登录、注册三处响应都带） |
| `frontend/src/api/admin.ts` | 新增 | `adminApi.listRooms/listUsers/listSummaries/listAudit/endRoom/deleteRoom/regenerateSummary` |
| `frontend/src/api/globalChat.ts` | 新增 | `globalChatApi.list({limit, beforeId})` / `post(body)` |
| `frontend/src/api/presence.ts` | 新增 | `presenceApi.beat()`（Q14=2 的心跳上报） |
| `frontend/src/hooks/useAdmin.ts` | 新增 | 四个 `useQuery`（分页参数进 queryKey，翻页即取）+ 三个 `useMutation`（成功后 `invalidateQueries(['admin-rooms'|'admin-summaries'])`） |
| `frontend/src/hooks/useGlobalChat.ts` | 新增 | `useQuery(['global-messages'], list)` + `useMutation(post)`；**兜底轮询 30 秒**（仅页面可见时，沿用 `useRosterSync` 写法：`document.visibilityState === 'visible'` 才真取） |
| `frontend/src/hooks/usePresenceBeat.ts` | 新增 | `PRESENCE_BEAT_MS = 60_000` 定时上报 `POST /api/presence`（仅可见 + 已登录才发）；挂在 `App.tsx` 顶层 |
| `frontend/src/hooks/useEventStream.ts` | 新增 | `new EventSource('/api/events')`；`onmessage` 解析 `type` → 按表 invalidate（`global_message` → `['global-messages']`）；`onerror` 不自己重连（`EventSource` 自带 3 秒重连）；`useEffect` 卸载时 `close()` |
| `frontend/src/components/GlobalChatDrawer.tsx` | 新增 | **右侧可收起侧栏面板（Q11=2，编辑器 Copilot 式）**：常规页面右缘的展开/收起按钮（Lucide `MessagesSquare`，带 `aria-expanded`）+ 抽屉本体（标题行「大屏 · 在线 N 人」+ 消息列表（作者 + 时间 + 正文，走 `MessageBubble` 同款视觉）+ 输入区（未登录：输入框禁用 + 「登录后可发言」+ 去登录带 `returnTo`）+ 关闭按钮）；**交流页不挂**（那里已有 `RoomSidePanel`，避免双右抽屉，见需求单 §10.1 细化点 2） |
| `frontend/src/pages/AdminPage.tsx` | 新增 | `/admin` 三 tab（房间 / 用户 / 纪要，另加「审计」tab 仅 Q7①）；tab 切换用既有 `live-drawer-tabs` 同款按钮组；每行右侧动作按钮（结束 / 删除 / 重生纪要），动作前**行内二次确认**（沿用 `DeviceBar` 的 `live-dock-confirm` 写法，不用原生 `confirm`——实测全仓 0 处原生弹窗） |
| `frontend/src/components/admin/AdminRoomTable.tsx` 等 3 个 | 新增 | 纯展示表格（列定义 + 空态 + 分页控件）；不放业务逻辑，便于开发者教学页讲「怎么加一列」 |
| `frontend/src/components/NavBar.tsx` | **不改**（Q12=2） | 顶栏**不加**管理后台入口；顶栏只多一个「大屏」面板开合按钮（与 `onToggleCollapsed` 同风格的 icon 按钮） |
| `frontend/src/components/SideBar.tsx` | 改 | `nav` 内追加常驻项「管理后台」（仅超管可见，Lucide `ShieldCheck`）；未登录/普通用户不可见 |
| `frontend/src/App.tsx` | 改 | 路由追加 `/admin`（沿用非交流页的 `layout` + 侧栏外壳） |
| `frontend/src/pages/RoomsPage.tsx` | **不改**（Q11=2 后无需） | 面板由 `App.tsx` 层挂载（右侧抽屉），房间列表页不承担挂载 |
| `frontend/src/pages/RoomLivePage.tsx` | 改 | 超管视角：`room.myRole === 'superadmin'` → 顶部 chip「管理视角 · 隐身」、治理按钮按房主权限开放（后端已放行）、**自身参与者格不进舞台**；**不渲染麦克风/摄像头/共享控件**，也不申请设备（Q4/Q8 补充：只管理）；进房前提示「管理员以客户端隐身方式进入，不发布音视频」；其余用户路径完全不变 |
| `frontend/src/styles/global.css` | 改 | 新增参数集中区（`--global-chat-*`：面板宽/行高/最大高；`--admin-*`：表格密度/行 hover 描边）+ 两处新块样式；所有值走既有令牌，禁止写死色值 |

## 6. 契约面清单（CR 定级基准物）

**新增对外可见面（L3 凭据）**

| 类别 | 清单 |
| --- | --- |
| 端点 | `GET /api/global-messages`、`POST /api/global-messages`、`GET /api/events`、`POST /api/presence`（Q14=2）、`GET /api/admin/rooms`、`GET /api/admin/users`、`GET /api/admin/summaries`、`GET /api/admin/audit`、`POST /api/admin/rooms/{id}/end`、`DELETE /api/admin/rooms/{id}`、`POST /api/admin/rooms/{id}/summary` |
| 响应字段 | `UserVO.role`（新增，`/me` 与登录/注册都带）；`RoomVO.myRole` 取值集合扩为 `host/moderator/participant/superadmin` |
| 错误码 | 新增 `RATE_LIMITED`（429）；其余复用（401 `UNAUTHORIZED`、403 `FORBIDDEN`、404 `NOT_FOUND`、409 `ROOM_ENDED`） |
| 数据模型 | `users.role` / `users.last_seen_at` / `room_visits` / `global_messages` / `admin_audit`（迁移 011） |
| 新传输形态 | `GET /api/events` 的 `text/event-stream`（首个 SSE 端点，须 ADR-0025） |
| 配置键 | `PRESENCE_ONLINE_SECONDS=120`（细则：2× 轮询周期；要严格 60 秒改这一个数）、`GLOBAL_CHAT_RATE_LIMIT=5`、`GLOBAL_CHAT_RATE_WINDOW_SECONDS=10`、`SSE_KEEPALIVE_SECONDS=15`、`SSE_SUBSCRIBER_QUEUE_MAX=32`、`SSE_MAX_SUBSCRIBERS=200`（`.env.example` 同步） |
| 验收清单 | 需求单 §4 的 E1~E12 |
| 示范动作 | 见 §7 教学契约 |

**明确不变的对外面**（防止实现期顺手改）：既有 6 组路由路径与出参字段、`/rooms/{id}/token` 的响应形状、`chat_messages` 的 `kind` 取值、容量口径（在册成员）、焦点来源规则、邀请码 TTL 上限（60 秒）。

## 7. 教学契约（不是教学页；教学页正文实现跑通后再写）

**使用者视角**
- 场景一句话：评审方想看「平台管理员」和「全服讨论」，浏览器里两个页面就能演完。
- 入口：**侧栏「管理后台」（仅超管可见）** → `/admin`；**顶栏「大屏」按钮 → 右侧可收起面板**（常规页面常驻，交流页不挂）。
- 输入与输出：后台三 tab 的列表与三动作（结束 / 删除 / 生成纪要）；大屏输入 ≤500 字 → 立刻出现在面板与所有在线用户的页面上。
- **一次典型使用动作（=验收示范）**：① 用演示超管登录 → 点顶栏「大屏」打开右侧面板发一条「大家好」→ 另一个浏览器（普通账号）**不刷新**（面板开着）也看到该条；② 超管打开 `/admin` → 房间 tab 对**别人**的房间点「结束」→ 该房转已结束，房内聊天栏出现一条「管理员结束了房间」的系统消息，审计 tab 出现一条 `room.end`；③ 超管进入一个**满员**房间 → 成员列表与人数不变、看不到超管 → 超管点「移出成员」生效（E2/E3/E4/E9）。
- **开发者视角（要改哪里）**：加一个管理动作 = ① `services/admin.py` 里加函数（内部先 `assert_superadmin`，动作后 `_audit`）② `routers/admin.py` 加一行路由 ③ 前端 `api/admin.ts` + `useAdmin.ts` 加一个 mutation ④ 页面加按钮（行内二次确认）；加一类 SSE 事件 = ① 落库后 `events.publish("<type>", {...})` ② 前端 `useEventStream` 的类型→queryKey 映射表加一行。

## 8. 失败与边界

| 场景 | 行为 |
| --- | --- |
| 超管进已结束房间 | 409 `ROOM_ENDED`（实时层不给；历史内容走只读接口，与普通用户一致） |
| 超管对不存在的房间取票/治理 | 404 `NOT_FOUND`（旁路不放宽"房间必须存在"） |
| 非超管调 `/api/admin/*` | 403 `FORBIDDEN`；未登录 401 `UNAUTHORIZED` |
| LiveKit 未配置（本地无凭据） | 与现口径一致：取票报错语义不变；后台「结束/删除」仍完成库侧动作，`livekitApplied` 字段如实为 false |
| 超管开麦（Q8① 下） | 音频可通但不进转写：worker 按 `lg-role=superadmin` 跳过、hidden 也可能让 worker 看不见；两处都记 changes.md 实测 |
| 删房后审计悬空 | `admin_audit.target_id` 指向已删房间（文档与后台 UI 均显示原标题快照，来自 `detail`） |
| 大屏发言太快 | 429 `RATE_LIMITED`（窗口内 ≥5 条）；前端提示「发得太快了，稍后再试」，输入内容**保留**不丢 |
| SSE 断线 / 服务重启 | `EventSource` 自动重连（3 秒）；重连期间 30 秒轮询兜底；多进程部署会漏通知（已知限制，落 ADR-0025） |
| 大屏历史消息为空 | 空态：一行文案 + 图标（无 emoji），不做骨架屏 |
| 超管尝试开麦/开摄像头 | 前端无控件；即便手改请求，Token 也无 `can_publish` → 服务端拒绝（E13 用例断言 grants） |
| 心跳停止（关页/断网） | 超过 `PRESENCE_ONLINE_SECONDS`（默认 120 秒）后该用户从「在线」消失；不产生额外写库 |
| 未登录用户开大屏面板 | 可看全部消息（Q13=1），输入区禁用并给「登录后可发言」+ 去登录（带 `returnTo`） |
| 未登录打开 `/admin` | 前端直接重定向到 `/login?returnTo=/admin`；后端仍然 401（双保险） |
| 满员房 + 超管 + 在册=容量 | 超管不被计入；新申请仍 409 `ROOM_FULL`（E4 用例断言） |

**回退方案**：整轮放弃 = 丢弃 `req/r012-superadmin-console` 分支（未合并）；若已合并 → `git revert` 对应提交（append-only，禁 amend/rebase）。**迁移 011 是前进式的**：本轮的 5 个表/列都是**新增**，回退时不需要 drop 也能让旧代码工作（旧代码不读新列）；`db_init --reset` 可完全重建。运行时回退开关：`GLOBAL_CHAT_RATE_LIMIT` 调大不解决根本问题，故**不设功能开关**，靠 revert 分支。

## 9. 视觉契约（令牌与动效）

- 令牌：**全部沿用** `frontend/src/styles/global.css` 既有变量（`--ink-900/800/700`、`--text/text-dim/text-mute`、`--accent`、`--warn/--danger/--ok`、`--line/--line-soft`、`--r-sm/md/lg`、`--s-1..--s-6`、`--t-fast/base/slow`、`--ease`）——本轮**不新增颜色/字号令牌**，只新增布局参数区：

| 位置 | 参数 | 默认（可调范围） | 参数写在哪（单点） | 降级 |
| --- | --- | --- | --- | --- |
| 右侧大屏面板 | `--global-chat-w` / 列表最大高 / 行间距 / 输入区高 | `360px`（320~420）/ `min(60vh, 520px)` / `--s-3` | `global.css` 顶部 `/* r012 参数区 */` | reduced-motion：新消息不做位移，只淡入 |
| 面板展开/收起 | 宽度 + 透明度（右侧滑入） | `--t-base` / `--ease` | 同上 | 直接显示/隐藏（无过渡） |
| 大屏新消息插入 | 淡入 + 上移 6px | 180ms / `--ease` | 同上 | 只淡入 |
| 管理表行 hover | 描边提亮（`--line` → `--accent-soft`） | `--t-fast` | 同上 | 无过渡（直接切换） |
| 删除/结束二次确认 | 行内展开（宽度 + 透明度） | `--t-base` | 复用 `live-dock-confirm` 既有参数 | 无过渡 |
| 面板入场 | 淡入 + 上移 8px | `--t-slow` | 同上 | 只淡入 |

- 图标：Lucide 唯一（`ShieldCheck` 管理后台 / `MessagesSquare` 大屏 / `Trash2` 删除 / `UserX` 结束）；每处图标旁必须有文字或 `title/aria-label`；**零 emoji**。
- 文案：称呼「你」；按钮动词短语（「结束房间」「生成纪要」「发布」）；禁内部词（轮次 / 里程碑 / 检查点 / cp-NNN / 作业 / 考核）；错误三分流沿用 `global-style.md` §8。
- **一次视觉验收动作（=验收示范）**：① 打开 `/admin`（桌面 1440×900）→ 三 tab 表格不横向溢出（`document.documentElement.scrollWidth === clientWidth`）；② 首页点顶栏「大屏」→ 面板从右侧滑出（实测 `--t-base` 240ms）、**不遮**房间卡片网格；③ 窄屏 375×812：面板改为覆盖式全宽 + 有关闭按钮；截图存 `docs/rounds/r012-superadmin-console/shots/`。

## 10. 待拍板与依赖

- 待拍板：需求单 §10 `ASK-r012-1` 的 **Q1~Q18**（本页按建议值展开；受影响小节已标注）。
- 依赖别的轮次：**r011 待合并**（`ab8edb5`，实现完成）——本分支从它开出；若你选择先合 r011 再合 r012，两者按顺序 `merge --no-ff` 即可（本分支已含 r011 全部提交）。

## 11. 变更记录

| 日期 | 版本 | 改了什么 | 依据 |
| --- | --- | --- | --- |
| 2026-09-20 | v1 | 建页：迁移 011 DDL + A/B/C 三组逐文件函数级设计 + 契约面清单 + 教学契约 + 失败边界与回退 + 视觉契约 | 需求单 v1 + `redirect-01.md` + 代码实测（行号、`VideoGrants.hidden`、级联 FK、错误码表） |
| 2026-09-20 | v2 | 按 `ASK-r012-1` 批复（需求单 §10.1）改写：① 超管**不发布音视频**（Token `can_publish=False`、界面无设备控件；§2.3/§2.4/§5/§8）② 在线改**前端 60 秒短轮询**（新增 `POST /api/presence` + `usePresenceBeat`；§2.6 整节重写，定性升 L3）③ 大屏面板改**右侧 Copilot 式抽屉**（§5/§7/§9）④ 管理后台入口**只放侧栏**、顶栏不加（§5）⑤ 基点合并 r011 cp-8/cp-8b（`e0c6598`） | 你 2026-09-20 的按编号批复 + 原话补充 |
