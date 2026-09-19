---
title: r005 实现页：容量按在册成员 + 房间事件系统消息
description: 判定点、函数签名与事务陷阱、系统消息文案、前端口径、验收数字与遗留。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
口径裁定见 `docs/03-decisions/r005-adr-0016-room-capacity-membership.md`；需求与验收见 `docs/00-requirements/r005-fix-capacity.md`；设计见 `docs/rounds/r005-fix-capacity/design.md`。本页是实现事实源。

## 1. 一句话口径

**房间人数 = 本库在册成员数**（`room_members.status='active'`）；上限 = `rooms.capacity`；LiveKit 只承担音视频承载，**不参与人数判定**。

## 2. 判定点（三处，全库内、同一事务、先锁房间行）

| 端点 | 函数 | 满员时 |
| --- | --- | --- |
| `POST /rooms/{id}/join-requests` | `services/rooms.py:request_join` | 写留痕 → **返回 `RoomFullNotice(capacity)`** → 路由 `fail(ERR_ROOM_FULL, …, 409)` |
| `POST /join-requests/{id}/approve` | `approve_join_request` | `raise AppError(ERR_ROOM_FULL, …, 409)`（该分支无留痕需求，异常安全） |
| `POST /rooms/{id}/token` | `issue_room_token` | **不再查 LiveKit**；在册 200 / 非在册 403 / 已结束 409 |

不变量：任何提交后 `count_active_members(room) <= rooms.capacity`。

## 3. 函数级

| 函数 | 签名要点 |
| --- | --- |
| `request_join(conn, actor, room_id, message) -> Union[JoinRequestVO, RoomFullNotice]` | 锁房间 → 不存在/已结束/已在房间/已有 pending → **在册 >= capacity：写「房间已满…」系统消息并返回 `RoomFullNotice`** → 否则插入申请（`UniqueViolation` → `ALREADY_PENDING`） |
| `approve_join_request(conn, actor, request_id) -> ApprovalResult` | 事务内新增：`count_active_members >= room.capacity → 409`；成功路径追加「{name} 加入了房间」 |
| `issue_room_token(conn, actor, room_id) -> RoomTokenVO` | 删除 `list_participant_identities` 调用与在场比较（`max_participants` 仍写进 Token，仅作承载兜底） |
| `leave_room` / `kick_member` / `transfer_host` / `end_room` | 各自事务内追加系统消息（见 §4） |
| `repositories/rooms.py:insert_message(conn, NewMessage)` / `get_display_name(conn, user_id)` | 系统消息写入与取名字（成员行不带名字） |
| `repositories/rooms.py` 三处列表 | 排序补 `id` 兜底（决定性排序，L1） |

## 4. 系统消息（`chat_messages.kind='system'`，`user_id` = 触发者）

| 事件 | 触发点 | 文案 | 事务 |
| --- | --- | --- | --- |
| 满员拒绝 | `request_join` | `房间已满（上限 {capacity} 人），本次申请未通过` | 与「判定」同事务，且**不抛错**（见 §5） |
| 加入 | `approve_join_request` | `{name} 加入了房间` | 同事务 |
| 离开 | `leave_room` | `{name} 离开了房间` | 同事务 |
| 被移出 | `kick_member` | `{name} 被移出房间` | 同事务 |
| 移交 | `transfer_host` | `{name} 成为房主` | 同事务 |
| 结束 | `end_room` | `房间已结束` | 同事务 |

计入未读；前端复用 `.chat-system`（居中灰字），**未改前端**。

## 5. 事务陷阱（cp-2/cp-3 实测踩过，务必记住）

`db_conn` 是 **psycopg_pool 的 `with connection()`**：**请求内抛异常 = 整条请求事务回滚**。
所以「状态变更 + 留痕」的支路里，只要还要抛错（如满员 409），同事务写的留痕就会被回滚掉 —— 实测：409 有了、库里查不到那条消息。
**正确做法**：让请求**正常返回**（把 409 交给路由层 `fail(...)`），事务正常提交；不要试图在 service 里 `conn.commit()`（在测试的外层 `Transaction` 上下文里会直接 `ProgrammingError`）。

## 6. 前端口径（三处同一数字）

| 位置 | 显示 |
| --- | --- |
| 列表卡（`RoomCard.tsx`） | `在册/容量`；满员时徽标「已满」并把人数徽标转警示色 |
| 交流页状态条（`RoomLivePage.tsx`） | `在册 / 容量 成员`（原来是「在场…在房间」） |
| 成员抽屉（`RoomSidePanel.tsx`） | **保留**「在房间里 / 不在房间」（LiveKit 事件驱动的在场标记，与容量无关） |

## 7. 验证数字（2026-09-19）

| 项 | 结果 |
| --- | --- |
| `pytest backend/tests -q` | **110 passed**（r004 基线 105 → 净 +5：容量两例翻转、接口一例重写、并发一例新增、系统消息四例） |
| `smoke.py` | **PASS 40/40**（补 r005 四步：填满、满员 409、满员留痕、加入/离开/被移出留痕） |
| 取票延迟（6 次采样） | 中位 **3.2ms**（min 2.9 / max 21.7）；改前 **1650ms** |
| 满员实测（真实 HTTP） | 满员房第 N+1 人申请 → 409 `ROOM_FULL`，系统消息 7 → 8 条 |
| `tsc --noEmit` / `npm run build` | exit 0 / exit 0 |
| 前端真机 | 列表卡「8/8 已满」；状态条「8 / 8 成员」；抽屉 8 条系统消息；在场标记正常（截图在 `%TEMP%\lg_r005\`） |

## 8. 遗留

1. 演示库里存在**历史超容量房间**（在册 > 容量，如 8 人房被手动加了第 9 个成员）：不会自动清理，表现为「已满且暂时无人能进」。是否清理属运维，等你一句话。
2. 本轮只为 6 类**房间事件**加系统消息；举手/焦点/共享仍走 r004 的通道，不进消息列表（如要，另开轮次）。
3. 未引入 `CAPACITY_CHECK_UNAVAILABLE`（库内判定不会失败）；若将来重新引入外部判定，必须 fail-closed（design §2 已写死）。
