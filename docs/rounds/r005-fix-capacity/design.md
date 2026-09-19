---
title: r005 设计：容量按在册成员（库为权威）+ 房间事件系统消息
description: 判定点、函数级改动、系统消息文案与事务位置、前端文案、并发与边界、验收映射；契约面（对外可见面/数据模型/边界/验收/回退）在本页 §11。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
本页是 r005 的设计事实源。口径裁定见 `docs/03-decisions/r005-adr-0016-room-capacity-membership.md`；需求与验收见 `docs/00-requirements/r005-fix-capacity.md`。

## 0. 本页怎么读

| 想找什么 | 去哪节 |
| --- | --- |
| 谁定义「人数」 | §1（唯一权威 + 不变量） |
| 哪里会拦人、拦成什么码 | §2（判定点与错误码） |
| 改哪些函数、怎么改 | §3（函数级）+ §4（系统消息） |
| 前端改什么 | §5；**不改**什么 §6 |
| 并发与边界 | §7 |
| 验收怎么算过 | §8（E1~E8 映射） |
| 契约面与回退 | §11 |

## 1. 口径与不变量

- **唯一权威**：本库 `room_members.status = 'active'` 的行数（「在册成员」= 本场已获准的人）。`rooms.capacity` 是上限（默认 8）。
- **LiveKit 不参与人数判定**：它只负责音视频承载与「此刻谁连着」（在场）。`services/livekit.py` 的 `list_participant_identities` 保留（在场标记、排障用），**不再用于容量**。
- **不变量 I1**：任何事务提交后 `count_active_members(room) <= rooms.capacity`。
- **不变量 I2**：容量判定与状态写入在**同一事务**、先 `lock_room`（复用 r001 的房间行锁），因此并发是串行的。

## 2. 判定点与错误码（三处，全库内）

| 端点 | 函数 | 判定 | 结果 |
| --- | --- | --- | --- |
| `POST /rooms/{id}/join-requests` | `request_join` | 在册 ≥ 容量 | **409 `ROOM_FULL`**「房间已满（上限 N 人）」（**新增**；同时写一条系统消息） |
| `POST /join-requests/{id}/approve` | `approve_join_request` | 在册 ≥ 容量 | **409 `ROOM_FULL`**（**新增**） |
| `POST /rooms/{id}/token` | `issue_room_token` | **移除** LiveKit 查询；在册即放行 | 200（在册）/ 403 `NOT_MEMBER` / 409 `ROOM_ENDED`（不变） |

- 不新增错误码；`ROOM_FULL` 已在 r001 错误码总表内（文案沿用「房间已满（上限 N 人）」）。
- 因容量判定改为库内 SQL，**不存在「外部校验失败」分支**；若将来重新引入外部判定，必须 fail-closed（本页即条款）。

## 3. 函数级改动（后端）

| 函数 | 改动 |
| --- | --- |
| `services/rooms.py:request_join(conn, actor, room_id, message)` | 在「已在房间 / 已有 pending」两道拦截之后、插入申请之前，增加：`with conn.transaction(): lock_room → assert_room_active → if count_active_members >= capacity: 写系统消息「房间已满…」→ raise 409 ROOM_FULL`。**满员拒绝也留痕**（Q3 的「留一个消息」）。 |
| `services/rooms.py:approve_join_request(conn, actor, request_id)` | 在既有事务内、`get_active_member` 检查之后插入：`if count_active_members >= capacity: raise 409 ROOM_FULL`；通过后写系统消息「{displayName} 加入了房间」。 |
| `services/rooms.py:issue_room_token(conn, actor, room_id)` | **删除** `livekit_service.list_participant_identities(...)` 与随后的容量比较；其余不变（`max_participants` 仍在 Token 里作承载侧兜底，语义降级为「音视频承载保护」，不再是人数权威）。 |
| `services/rooms.py:leave_room(...)` | 事务内追加系统消息「{displayName} 离开了房间」。 |
| `services/rooms.py:kick_member(...)` | 既有事务内追加「{displayName} 被移出房间」（与 `deactivate_member` 同事务）。 |
| `services/rooms.py:transfer_host(...)` | 既有事务内追加「{displayName} 成为房主」。 |
| `services/rooms.py:end_room(...)` | 既有事务内追加「房间已结束」。 |
| `repositories/rooms.py` | 新增 `insert_system_message(conn, room_id, actor_id, body, now) -> str`（`kind='system'`）；复用 `count_active_members`。 |
| `services/livekit.py` | **不改代码**；仅在文档里标注「不再参与容量判定」。 |

## 4. 系统消息（Q2/Q3 的「留一个消息」）

- **存储**：`chat_messages` 既有表（`kind IN ('chat','system')`，`user_id NOT NULL` → 记**触发者**：申请人 / 房主）；与状态变更**同一事务**（要么都成，要么都不成）。
- **文案表**（唯一来源；前端只渲染不判断）：

| 事件 | 文案 |
| --- | --- |
| 满员拒绝 | `房间已满（上限 {capacity} 人），本次申请未通过` |
| 加入 | `{name} 加入了房间` |
| 离开 | `{name} 离开了房间` |
| 被移出 | `{name} 被移出房间` |
| 移交 | `{name} 成为房主` |
| 结束 | `房间已结束` |

- **排序与分页**：与普通消息同表同序（`created_at`），所以历史分页与「加载更早」天然覆盖；系统消息**计入未读数**（简单、与「都在消息列表里」一致；若你要排除，改一处即可）。
- **前端**：`components/live/MessageBubble.tsx` 已有 `kind === 'system'` 分支（居中灰字），**不改**。
- **边界**：本轮不为举手/焦点/共享加系统消息（那些是房内即时状态，不是房间事件）。
- **事务细节（实现要点）**：五类「成功事件」在状态变更的同一事务内写消息；**「满员拒绝」例外** —— 它要抛 409，所以顺序是「退出判定事务 → 单独事务写消息 → 抛错」，用例专门锁死这一条。

## 5. 前端改动

| 文件 | 改动 |
| --- | --- |
| `pages/RoomLivePage.tsx` | 状态条由「{在场} / {容量} 在房间」改为「**{在册} / {容量} 成员**」；`title` 文案改为「本场已获准进场的人数（= 在册成员）」。在场人数仍在成员抽屉看。 |
| `components/RoomCard.tsx` | 满员（在册 = 容量）时：占用条 100% + 加「**已满**」徽标（复用 `.chip-warn`）；数字口径不变（已是 `memberCount/capacity`）。 |
| `components/live/RoomSidePanel.tsx` | **不改**：抽屉的「在房间里 / 不在房间」是在场标记（LiveKit 事件驱动），与容量无关。 |

## 6. 明确不改

- 不改房间生命周期（结束/只读/纪要路线）；不改 r004 的房内能力与系统消息之外的通道；不加依赖；不新增错误码；不动 `AGENTS.md` 的命令（数字写死问题在 r005 测试体系轮处理）。

## 7. 并发与边界

1. **并发批准**：两个批准同时到 → `lock_room` 串行 → 第二个看到在册 = 容量 → 409（I1 成立）。
2. **并发申请**：满员时两个申请同时到 → 都读到满 → 都 409（各留一条系统消息；这是可接受的重复提示，比漏拦安全）。
3. **满员 + 已有 pending 的申请**：房主点批准 → 409；既有 pending 申请保持 `pending`（不自动拒），房主可手动拒。
4. **房间结束时**：所有容量判定先 `assert_room_active` → 409 `ROOM_ENDED` 优先（与现状一致）。
5. **在册满但没人在线**：申请被拒（Q1=2 的直接后果）；成员抽屉会显示「不在房间」，功能页与教学页写明这一口径。
6. **被移出/离开释放名额**：`status` 转 `inactive` 即在册数 -1 → 新申请可进（无需额外动作）。
7. **房主自己**：房主是 `host` 在册成员，占一个名额（现状不变）。

## 8. 验收映射（E1~E8 → 证据）

| 验收 | 证据来源 | 级别 |
| --- | --- | --- |
| E1 列表卡满员态与数字 | 前端真机截图 + `memberCount` 断言 | N |
| E2 满员申请 409 + 系统消息 | `pytest` 用例（接口层）+ `smoke.py` | I |
| E3 并发不变量 I1 | `pytest` 并发用例（两连接） | I |
| E4 取票提速且行为不变 | 实测中位数（改前 1650ms）+ 用例（200/403/409） | I/N |
| E5 六类系统消息 | `pytest` 用例（读库断言 `kind='system'`）+ 刷新一致 | I |
| E6 在场标记不受影响 | 真机（两个浏览器，其一关闭后另一端标记变化） | N |
| E7 前端文案统一 | 真机截图（列表卡 + 状态条 + 聊天系统消息） | N |
| E8 门禁三项 | `pytest` / `smoke` / `tsc`+`build` 输出 | S/I |

## 9. 非目标

排队系统、占座超时回收、按主题分池、容量动态调整、系统消息的国际化、把在场数写进列表接口。

## 10. 变更记录

| 日期 | cp | 变更 | 依据 |
| --- | --- | --- | --- |
| 2026-09-19 | cp-0 | 建页：口径/判定点/函数级/系统消息/前端/并发/验收映射 | 你的批复 Q1~Q5（`2 / 2 1 / 1 1`） |
| 2026-09-19 | cp-2 | 系统消息实现细节：满员拒绝最初写成「先提交消息再抛 409」 | 必须：抛错会回滚同事务里的消息，Q3 的留痕会丢 |
| 2026-09-19 | cp-3 | **改为「满员不抛错」**：`request_join` 返回 `RoomFullNotice`，路由用 `fail(409)` 正常返回（原方案的显式 `conn.commit()` 在测试外层事务里非法，且属补丁式） | 实测：留痕在真实请求下仍丢；正确做法是让请求事务正常提交 |
| 2026-09-19 | cp-1 | **L1**：`repositories/rooms.py` 三处列表排序加 `id` 兜底（决定性排序；对外面与验收不变，仅让分页稳定） | 实测：`test_list_rooms_pagination` 因同一秒创建的多个房间而「相邻两页重叠」 |

## 11. 契约面清单（CR 定级的基准物）

| 面 | 内容 | 变化 |
| --- | --- | --- |
| 对外可见面 | `POST /rooms/{id}/join-requests` 新增 409 `ROOM_FULL`；`POST /join-requests/{id}/approve` 新增 409 `ROOM_FULL`；`GET /messages` 会多出 `kind='system'` 行；状态条与列表卡文案变化 | **变**（L3，已获你批准） |
| 数据模型 | 无新表/无新列/无迁移 | 不变 |
| 模块边界与依赖 | `services/rooms.py` 不再调 `livekit.list_participant_identities`；零新依赖 | 收窄 |
| 验收标准 | 需求单 §5 E1~E8 | 新 |
| 示范动作 | 满员时第 9 人申请被拒 + 消息列表出现系统消息；取票近即时返回 | 新 |
| 回退方案 | 单个提交可 revert：`git revert <cp 提交>` 即可回到「申请不校验 + 取票查 LiveKit」；无数据迁移需回滚 | 线性、无副作用 |
