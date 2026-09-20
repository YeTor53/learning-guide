---
title: r012 实现页：超管身份与在线口径（首版，随 cp 增量补齐）
description: users.role 与 last_seen_at、room_visits/global_messages/admin_audit 三表、提权脚本与演示超管、在线心跳接口与前端 60 秒上报——r012 的实现事实源。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-20
---

<!-- overview -->
需求见 `docs/00-requirements/r012-superadmin-console.md`（§10.1 = 你 2026-09-20 的逐条批复）；逐文件设计 `rounds/r012-superadmin-console/design.md`；决定 **ADR-0024**（超管隐身与旁路收敛）。本页随 cp 增量长齐：**本文只写已经落地的事实**，未落地的一律列在 §5。
一句话（当前进度）：**超管身份、在线口径与「隐身进房 + 旁路治理」已落地**（迁移 011/012 + `POST /api/presence` + 前端 60 秒心跳 + hidden Token + `room_visits`）；管理后台、大屏聊天与 SSE 在 cp-4/cp-5 落地，前端在 cp-6。

## 1. 身份（迁移 011/012；ADR-0024 D1）

| 面 | 要点 |
| --- | --- |
| `users.role` | `TEXT NOT NULL DEFAULT 'user'`，`CHECK (role IN ('user','superadmin'))`；判据唯一入口 `services/roles.py::is_superadmin`（禁止别处直接比较字符串） |
| 出参 | `UserVO.role`（`/api/auth/me`、登录、注册三处响应都带）——前端据此显示入口；**服务端仍强制校验**，前端可见性不是安全边界 |
| 演示超管 | `012_r012_seed_superadmin.sql`：`admin@example.com` / 口令同其它演示账号（`demo1234`）/ `id = usr_demo_admin` / `display_name = 平台管理员`；重复 seed 会把它的角色重置为 `superadmin` |
| 提权脚本 | `python backend/scripts/grant_superadmin.py --email <邮箱> [--revoke] [--role user\|superadmin]`：打印「邮箱：改前 → 改后（影响 n 行；id=…）」；邮箱不存在 → 退出码 2、零副作用 |
| 迁移 011 其余对象 | `room_visits`（超管进房旁路，cp-3 写入）、`global_messages`（大屏聊天，cp-5）、`admin_audit`（管理审计，**不 FK 到 rooms**） |

## 2. 在线口径（Q14=2：前端短轮询；ADR-0024 未涉，口径在 design §2.6）

| 面 | 要点 |
| --- | --- |
| 写入点 | 只有一处：`POST /api/presence`（登录必需、无请求体）→ `services/presence.py::touch` → `users.last_seen_at` |
| 判据 | 在线 = `now - last_seen_at ≤ PRESENCE_ONLINE_SECONDS`（默认 **120 秒** = 2× 前端周期，容一次丢包；改这个数即可调节）；无心跳（NULL）一律离线 |
| 前端 | `hooks/usePresenceBeat.ts`：`PRESENCE_BEAT_MS = 60_000`，仅「已登录 + 页面可见」时上报（沿用 `useRosterSync` 的可见性判据），失败静默；挂载点在 `App.tsx`（全站一次） |
| 端点出参 | `{"ok": true, "lastSeenAt": "<ISO>"}`（前端不依赖返回值，只作观测） |
| 已知限制 | 判据是"最后一次上报"，最坏情况离线识别延迟 ≈ 120 秒；多端登录同一账号时会互相刷新（按账号算，不按端） |

## 3. 隐身进房与旁路治理（cp-3；ADR-0024 D2/D3/D4）

| 面 | 要点 |
| --- | --- |
| 取票 | `POST /api/rooms/{id}/token` 超管分支：跳过「活跃成员」校验（**可进满员房**）→ 写一条 `room_visits`（已有未关闭记录则复用）→ 签**隐身只读** Token。房间不存在仍 404、已结束仍 409 |
| Token grants（超管） | `hidden=True`（对其它参与者不可见）· `canPublish=False` · `canPublishData=False`（不发声不出画不发数据）· `roomAdmin=False`（不借 LiveKit 管控权）· `attributes={'lg-role': 'superadmin'}`；`maxParticipants` 仍取房间容量（仅承载兜底） |
| 不占人数 | 超管**不写 `room_members`** → `count_active_members` 不变，「在册 ≤ 容量」不变量不受影响（ADR-0024 D5）；满员房新申请仍 409 `ROOM_FULL` |
| 旁路校验（两处收敛） | `assert_room_role` / `assert_manager_role` 见超管即放行；前者返回**不落库的虚拟成员行**（`role='host'`，`id=''`）。踢人 / 改角色 / 移交 / 结束房间 / 看待批申请因此全部自动放开（ADR-0024 D4） |
| 视角 | 列表与详情把 `myRole` 填成 `'superadmin'`（`effective_role`）；`pendingCount` 对超管可见 |
| 离开 / 结束 | 超管 `POST /rooms/{id}/leave` 只收口访问记录（无成员行可置 inactive）；`end_room` 在既有连带动作后追加 `close_all_visits` |
| 转写 | `agents/transcriber.py::TranscriberPool._maybe_start` 增加 `attributes['lg-role'] == 'superadmin'` 跳过（双保险：`hidden` 参与者通常对 worker 也不可见；且超管本就没有音频轨） |
| 未改动的面 | 房内发言/看消息仍走 `messages.py::_guard_active_member`（超管**不在**房间里说话，只在大屏发言，Q4=1）；前端设备控件与「管理视角」标识在 cp-6 |

## 4. 管理后台（cp-4；Q5=1 / Q6=1 / Q7=1 / Q16=1）

| 面 | 要点 |
| --- | --- |
| 三列表 | `GET /admin/rooms`（房主名 / 在册人数 / 待批数 / 纪要状态 / 房间码，`status=&q=&limit=&offset=`）、`GET /admin/users`（角色 / 最后心跳 / 参与房间数 / 发言数 / 全服发言数，`q=&online_only=&limit=&offset=`）、`GET /admin/summaries`（房间标题 / 状态 / 模型 / 字数，`status=`）；另 `GET /admin/audit`（`action=`） |
| 三动作 | `POST /admin/rooms/{id}/end`（复用 `rooms_service.end_room`）、`DELETE /admin/rooms/{id}`（硬删：本库行级联删 + 提交后删 LiveKit 房间）、`POST /admin/rooms/{id}/summary`（复用纪要服务） |
| 鉴权 | 每个端点 `Depends(current_superadmin)`：未登录 401 `UNAUTHORIZED` / 非超管 403 `FORBIDDEN`（**不靠前端隐藏入口**） |
| 审计 | 三动作各写一条 `admin_audit`（`action` 词表在 `services/admin.py::ADMIN_ACTIONS`，与业务动作同一事务）；删房的快照（标题/房主/人数/消息数/纪要数）写进 `detail.snapshot`——删完仍可追溯；`target_id` **不 FK** 到 rooms，删房后允许悬空 |
| 查询参数 | 一律 snake_case（`online_only=1`、`status=ended`、`limit/offset`），与既有 `mine=` / `status=` 同口径；出参 camelCase |
| 分页 | 四张列表统一 `{items, total, limit, offset}`，`limit` 1~100（默认 20） |

## 5. 全服大屏聊天与 SSE（cp-5；ADR-0025）

| 面 | 要点 |
| --- | --- |
| 存储 | `global_messages`（迁移 011）：`body` 1~500 字 CHECK；索引 `(created_at DESC)` + `(user_id, created_at DESC)`。**不复用 `chat_messages`**（那张表 `room_id NOT NULL`） |
| 可见性 | `GET /api/global-messages` **未登录可读**（公开面）、按时间**正序**返回、`before_id` 游标翻历史；`POST` 需登录（401） |
| 在线点 | 每条带 `authorOnline`：该用户最近有心跳（`users.last_seen_at` 在 `PRESENCE_ONLINE_SECONDS` 内）为真（Q13=1：全部可见 + 在线点） |
| 限流 | 窗口内每人 ≤ `GLOBAL_CHAT_RATE_LIMIT`（默认 5）/ `GLOBAL_CHAT_RATE_WINDOW_SECONDS`（默认 10 秒）；超限 429 `RATE_LIMITED` 且**不落库**；计数走**库查询**（重启不放大额度） |
| 落库与通知顺序 | 先落库（唯一真相）→ 提交后 `events.publish("global_message", {"id": …})`；通知丢失不影响数据 |
| SSE 协议 | `GET /api/events`（未登录也可订阅）：响应头 `text/event-stream` + `no-store` + `X-Accel-Buffering: no`；首帧 `retry: 3000`；事件名固定 `notify`；`data` = `{"type":…,"payload":{最小载荷}}`；无事件时每 `SSE_KEEPALIVE_SECONDS`（默认 15）秒一行 `: ping` |
| 进程内 pub/sub | `services/events.py`：订阅者集合 + 每连接队列（上限 `SSE_SUBSCRIBER_QUEUE_MAX`，满了**丢最旧**并记日志）；订阅者总数上限 `SSE_MAX_SUBSCRIBERS`（超了 503，不静默丢） |
| 已知限制 | **单进程**内存广播：多进程/多机部署会漏事件（ADR-0025 D4）；前端靠 `EventSource` 自动重连 + 30 秒轮询兜底 |

## 6. 端点清单（当前已落地）

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| POST | `/api/presence` | 登录 | 心跳上报（未登录 401 `UNAUTHORIZED`） |
| POST | `/api/rooms/{id}/token` | 登录 | **既有端点**：cp-3 起超管走隐身只读分支（响应形状不变） |
| GET | `/api/admin/rooms` | 超管 | 房间列表（含房主名 / 人数 / 待批 / 纪要状态） |
| GET | `/api/admin/users` | 超管 | 用户列表（含角色 / 最后心跳 / 统计；`online_only=1` 只看在线） |
| GET | `/api/admin/summaries` | 超管 | 纪要列表（含房间标题 / 状态 / 模型 / 字数） |
| GET | `/api/admin/audit` | 超管 | 管理动作流水 |
| POST | `/api/admin/rooms/{id}/end` | 超管 | 结束任意房间（+ 审计） |
| DELETE | `/api/admin/rooms/{id}` | 超管 | 硬删房间（+ 审计；不可逆） |
| POST | `/api/admin/rooms/{id}/summary` | 超管 | 生成 / 重生讨论纪要（+ 审计） |
| GET | `/api/global-messages` | 任意（含未登录） | 大屏消息列表（正序；`limit=` / `before_id=`） |
| POST | `/api/global-messages` | 登录 | 发言（1~500 字；超限 429 `RATE_LIMITED`） |
| GET | `/api/events` | 任意（含未登录） | SSE 通知流（`text/event-stream`，只推通知） |

## 7. 用例与实测

| 项 | 命令 / 用例 | 实测 |
| --- | --- | --- |
| 迁移 | `python backend/scripts/db_init.py --seed` | `[migrate] 011_r012_superadmin_global_chat, 012_r012_seed_superadmin`；`schema_migrations 12`（2026-09-20 实测） |
| 身份 | `pytest backend/tests -q -k "superadmin or presence"` | 见 `rounds/r012-superadmin-console/changes.md` §3（实测数字） |
| 提权脚本 | `grant_superadmin.py --email host@example.com` → `--revoke`；`--email nobody@example.com` | `user → superadmin（影响 1 行）` / `superadmin → user（影响 1 行）` / 退出码 2「找不到账号」（实测原样） |
| 前端 | `npx tsc --noEmit` | exit 0 |

## 8. 本页尚缺（随增量补齐，见需求单 §9 cp 切分）

- cp-6：前端（`/admin` 页、右侧大屏抽屉、仅超管可见的侧栏入口、超管管理视角）。

## 9. 变更记录

| 日期 | 版本 | 改了什么 | 依据 |
| --- | --- | --- | --- |
| 2026-09-20 | v1（cp-2） | 建页：身份（`users.role` + 提权脚本 + 演示超管 + 迁移 011/012 对象）与在线口径（`POST /api/presence` + 前端心跳 + 判据窗口） | 需求单 §10.1（Q1/Q14/Q15）、design §1/§2.6、ADR-0024 |
| 2026-09-20 | v4（cp-5） | 追加 §5 大屏聊天与 SSE：存储与可见性、在线点、限流（库计数）、落库→通知顺序、SSE 帧协议、进程内 pub/sub 与单进程限制；ADR-0025 落地 | 需求单 §10.1（Q13/Q11/Q14）、design §4、ADR-0025 |
| 2026-09-20 | v3（cp-4） | 追加 §4 管理后台：三列表（房间/用户/纪要 + 审计）、三动作（结束/硬删/重生纪要）、`current_superadmin` 鉴权、审计词表与删房快照、查询参数口径 | 需求单 §10.1（Q5/Q6/Q7/Q16）、design §3、ADR-0024 D6 |
| 2026-09-20 | v2（cp-3） | 追加 §3 隐身进房与旁路治理：hidden/只读 Token、`room_visits`、两处旁路收敛、`effective_role`、离开/结束的访问收口、worker 跳过超管 | 需求单 §10.1（Q2/Q3/Q4/Q8）、design §2.2~§2.4、ADR-0024 D2~D5 |
