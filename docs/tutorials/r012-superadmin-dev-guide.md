---
title: r012 开发者教学：加一个管理动作、加一类实时通知
description: 管理后台的两条扩展线（新动作 / 新 SSE 事件）各要改哪几处，附超管隐身的三道拦线与常见踩坑。
type: tutorial
status: draft
owner: 陀梓皓
updated: 2026-09-20
rounds: [r012]
---

<!-- overview -->
事实源：`docs/02-modules/r012-superadmin-console.md`（实现页）、`docs/rounds/r012-superadmin-console/design.md`（逐文件设计）、ADR-0024（超管隐身）、ADR-0025（SSE 口径）。
本页给「要动手改」的人：两条扩展线各改哪几处、隐身为什么有三道拦线、以及本轮踩过的坑。

## 1. 加一个**管理动作**（以「封禁用户」为例）

1. 审计词表：`backend/app/services/admin.py::ADMIN_ACTIONS` 加 `"user.ban"`（**所有管理动作必须登记**，后台审计分区按它显示）。
2. 服务层：`services/admin.py` 加 `def ban_user(conn, actor, user_id)`，**第一行**必须 `roles_service.assert_superadmin(actor)`；动作与 `_audit(...)` 放**同一个事务**（有动作必有流水）。
3. 仓储：需要新 SQL 就加到 `repositories/admin.py`（本文件只放参数化 SQL，不写业务判断）。
4. 路由：`api/routers/admin.py` 加一行 `@router.post("/users/{user_id}/ban")`，依赖 `current_superadmin`（未登录 401 / 非超管 403 自动生效）。
5. 前端：`api/admin.ts` 加方法 → `hooks/useAdmin.ts` 加 mutation（`onSuccess` 里失效列表与审计）→ `pages/AdminPage.tsx` 加按钮（破坏性动作走**行内二次确认**，不用原生 `confirm`）。
6. 用例：`backend/tests/test_admin_api.py` 加「成功一次 + 非超管 403 + 审计有一条」。
7. 文档：模块实现页补一行、`changes.md` 记一行；改到对外可见面（新端点/新字段）要在 design 的契约面清单登记。

## 2. 加一类**实时通知**（SSE）

1. 落库后（事务提交之后）调 `services/events.py::publish("<type>", {"id": ...})` —— **只带最小载荷**，别把整条数据塞进去。
2. 前端 `hooks/useEventStream.ts` 的映射表里加一行：`type` → 要失效的 `queryKey`（前端收到通知后照旧走 HTTP 拉真相）。
3. 不要新增 SSE `event:` 名：协议固定 `notify`，分派靠 `data.type`（否则前端要维护多套监听）。
4. 用例：`events.subscribe()` → `publish(...)` → `await queue.get()` 断言载荷；**不要用 TestClient 去读永不结束的流**（本机实测会挂死，见 §4）。

## 3. 超管隐身靠三道拦线（缺一即「隐身失败」）

| # | 拦线 | 位置 | 为什么 |
| --- | --- | --- | --- |
| 1 | 不写 `room_members` | `services/rooms.py::_record_admin_visit`（写 `room_visits`） | 成员列表 / 人数 / 待批可见性都以 `room_members` 为准；不写它，这些都天然不含超管 |
| 2 | Token 隐身 + 禁发布 | `services/livekit.py::issue_token(hidden=True, can_publish=False, ...)` | 其他客户端的参与者列表来自 LiveKit；不隐身就会在轨道层露出来 |
| 3 | worker 过滤 | `agents/transcriber.py::TranscriberPool._maybe_start` | 转写/纪要素材不收超管（他没有音频轨，属性过滤是双保险） |

配套：`assert_room_role` / `assert_manager_role` 两个函数里放行超管（**别在各调用点散加 `if is_superadmin`**，否则必然漏一处），前端 `myRole === 'superadmin'` 只用来显示入口与治理按钮，**不是安全边界**。

## 4. 本轮踩过的坑（实测）

1. **永不结束的流不要走 TestClient**：`GET /api/events` 的生成器不结束，`client.stream()` 读完一行就 break 会挂到超时（实测 pytest 卡 280 秒）。改法：直接 `await router.stream_events(request, user=None)` 拿 `response.body_iterator`，逐帧 `anext()` 断言后 `aclose()`。
2. **订阅前的事件会丢**：`publish` 只投给当前订阅者；这是有意的（通知不保证送达，HTTP 才是真相）。写用例要先订阅再 publish。
3. **前端查询参数是 snake_case**：后台接口沿用 `mine=` / `status=` 的口径（`online_only=1`、`before_id=...`），出参才是 camelCase。
4. **`Role` 与 `ViewerRole` 是两个概念**：`Role` 只是成员角色（host/moderator/participant），超管的视角值单独用 `ViewerRole`；把 `superadmin` 塞进 `Role` 会让成员图标表到处报缺键。

## 4.5 想改「隐身」相关行为时，先跑这条

`py -3 backend/scripts/verify_r012_superadmin_invisible.py`（PASS 17/17）会在真 Chrome 里复核三层拦线：
界面层（舞台 / 在册 / 成员抽屉）、**LiveKit 媒体层**（服务端 `hidden=true`、`canPublish=false`、`tracks=[]`）、
以及面板动效的降级。改 `issue_token` 的 grants、`DeviceBar.superadminMode`、`excludeIdentity` 之后跑它，比手点两个浏览器快也更可信。
另外两个脚本也值得挂上：`smoke.py`（58 步，含超管/后台/大屏）、`pytest backend/tests -q`（201 项）。

## 5. 变更记录

| 日期 | 版本 | 改了什么 | 依据 |
| --- | --- | --- | --- |
| 2026-09-20 | v1（cp-6） | 建页：两条扩展线步骤、三道隐身拦线、四个实测坑 | r012 cp-2~cp-6 实现过程 |
| 2026-09-20 | v2（cp-7b） | 追加 §4.5：改隐身相关行为前先跑 `verify_r012_superadmin_invisible.py` | cp-7b 实测 |
