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
一句话（当前进度）：**超管身份与在线口径已落地**（迁移 011/012 + `POST /api/presence` + 前端 60 秒心跳）；隐身进房、管理后台、大屏聊天与 SSE 在 cp-3~cp-6 落地。

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

## 3. 端点清单（当前已落地）

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| POST | `/api/presence` | 登录 | 心跳上报（未登录 401 `UNAUTHORIZED`） |

## 4. 用例与实测

| 项 | 命令 / 用例 | 实测 |
| --- | --- | --- |
| 迁移 | `python backend/scripts/db_init.py --seed` | `[migrate] 011_r012_superadmin_global_chat, 012_r012_seed_superadmin`；`schema_migrations 12`（2026-09-20 实测） |
| 身份 | `pytest backend/tests -q -k "superadmin or presence"` | 见 `rounds/r012-superadmin-console/changes.md` §3（实测数字） |
| 提权脚本 | `grant_superadmin.py --email host@example.com` → `--revoke`；`--email nobody@example.com` | `user → superadmin（影响 1 行）` / `superadmin → user（影响 1 行）` / 退出码 2「找不到账号」（实测原样） |
| 前端 | `npx tsc --noEmit` | exit 0 |

## 5. 本页尚缺（随增量补齐，见需求单 §9 cp 切分）

- cp-3：超管隐身进房（`hidden` Token + `room_visits`）、两处旁路校验、取票分支、worker 跳过超管。
- cp-4：管理后台三列表 + 结束/删除/重生纪要 + `admin_audit` 写入。
- cp-5：全服大屏聊天（`global_messages`）+ SSE（`GET /api/events`）+ 限流。
- cp-6：前端（`/admin` 页、右侧大屏抽屉、仅超管可见的侧栏入口、超管管理视角）。

## 6. 变更记录

| 日期 | 版本 | 改了什么 | 依据 |
| --- | --- | --- | --- |
| 2026-09-20 | v1（cp-2） | 建页：身份（`users.role` + 提权脚本 + 演示超管 + 迁移 011/012 对象）与在线口径（`POST /api/presence` + 前端心跳 + 判据窗口） | 需求单 §10.1（Q1/Q14/Q15）、design §1/§2.6、ADR-0024 |
