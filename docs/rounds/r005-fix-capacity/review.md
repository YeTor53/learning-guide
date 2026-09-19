---
title: r005 审查报告（阶段 3）
description: E1~E8 逐条证据、规则核对、文档对账、视觉对账、两栏处置清单与合并指引（2026-09-19 定稿）。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
对照需求单 §5 的 E1~E8 逐条给证据。**状态：定稿**（等合并后由索引表转 closed）。

## 1. 验收对账

| 条目 | 实现位置 | 证据 | 结论 |
| --- | --- | --- | --- |
| E1 列表卡满员态与数字 | `components/RoomCard.tsx` | 真机（Playwright，1440×900）：`r005 满员取证 c600f` 卡片文案 = `… 已满 … 8/8 已满 …`；截图 `list-card-full.png` | **通过** |
| E2 满员申请 409 + 留痕 | `services/rooms.py:request_join` + `api/routers/rooms.py` | 真实 HTTP：满员房第 N+1 人申请 → **409 `ROOM_FULL`**，系统消息 **7 → 8**（新增「房间已满（上限 8 人），本次申请未通过」）；用例 `test_capacity_is_enforced_by_membership` / `test_rooms_service.py::test_request_join_rejected_when_full` / `test_room_events_messages.py::test_full_room_rejection_leaves_system_message`；smoke 3 条 | **通过** |
| E3 并发不变量 | `test_rooms_concurrency.py` | 新增 `test_concurrent_approve_respects_capacity`：capacity=3、在册 2、两条待批并发批准 → `["ROOM_FULL","ok"]`，在册 ≤ 容量 | **通过** |
| E4 取票提速且行为不变 | `services/rooms.py:issue_room_token` | 实测 6 次采样：中位 **3.2ms**（min 2.9/max 21.7），改前 **1650ms**；用例把 `list_participant_identities` 打成抛错仍 200（证明不再调用）；非在册 403 / 已结束 409 由既有用例覆盖；smoke 「成员取 Token → 200 / 结束后 409」 | **通过** |
| E5 六类系统消息 | `services/rooms.py` 六处 + 用例 `test_room_events_messages.py`（4 例） | 库内断言 + 页面断言：`['成员1 加入了房间', … ,'房间已满（上限 8 人），本次申请未通过']`（真机抽屉 8 条）；smoke「加入/离开/被移出也留痕」 | **通过** |
| E6 在场标记不受影响 | `RoomSidePanel.tsx`（未改） | 真机成员抽屉：`取证房主 房主 在房间里` / `成员1 成员 不在房间 …`（截图 `members-presence.png`） | **通过** |
| E7 前端文案统一 | `RoomLivePage.tsx` / `RoomCard.tsx` | 真机状态条 = `8 / 8 成员`（在册口径）；列表卡「已满」；抽屉系统消息灰字（截图 `live-statusbar.png`、`chat-system-messages.png`） | **通过** |
| E8 门禁 | 迁移 005 + 守卫用例 | `pytest` **111 passed**（连跑两次稳定）；`smoke` **PASS 40/40**；`tsc --noEmit` + `npm run build` exit 0；`db_init` 应用 005 成功 | **通过** |

## 2. 规则核对（AGENTS.md）

| 规则 | 核对方式 | 结论 |
| --- | --- | --- |
| 未批不实现；每处改动挂 `rNNN` | 提交信息 `[Req: r005]`；需求单 §3 有你 Q1~Q5 批复回读 | **通过** |
| 一次提交一个逻辑增量；`git add` 具体路径 | `git log`：cp-0/cp-1/cp-2/cp-3/cp-4 各一提交 | **通过** |
| 零新依赖、不改端口 | `package.json` / `requirements*.txt` 无变化；端口仍 8000/5173 | **通过** |
| 密钥不入库 | `git grep -nE "API_SECRET\|API_KEY" -- backend/app frontend/src` 仅命中文档与 config 变量名 | **通过** |
| 文档与代码同提交 | 每个 cp 提交都含对应文档 | **通过** |
| 行为变更记 ADR + 模块页变更记录 | 新增 ADR-0016 + ADR-0012 追加 D9 指路行 | **通过** |

## 3. 文档对账

| 项 | 结论 |
| --- | --- |
| 模块轴：设计页 / 实现页 / 功能页 / 使用者教学页 / 开发者补节 | **齐**（`rounds/r005-fix-capacity/design.md`、`02-modules/r005-fix-capacity{,-features}.md`、`tutorials/r005-capacity-and-events.md`、`r002-livekit-dev-guide.md §9`） |
| 轮次轴：design / changes / review + ADR-0016 | **齐** |
| 索引 + 模块 README + roadmap + 覆盖矩阵无 planned | cp-4 已回填 |

## 4. 视觉对账

| 组 | 方式 | 结果 |
| --- | --- | --- |
| 文案口径 | 真机截图三张 | 列表卡「已满 / 8/8 已满」、状态条「8 / 8 成员」、抽屉系统消息 | 
| 满员态样式 | 复用既有 `.chip-warn` | **通过**（未新增令牌/图标） |
| 零 emoji / 单一图标库 | 扫描 | 仅 Lucide（`Users`） | **通过** |

## 5. 留给用户的两栏处置清单

**已落地可保留的增量（提议保留）**

1. 容量口径改为「本库在册成员」（ADR-0016），申请/批准两处封顶、不变量用例与并发用例齐全。
2. 取票路径去掉 LiveKit 查询：**1650ms → 3.2ms**（顺带解决「连上服务慢」），并堵住「外部查询失败就放人」的洞。
3. 六类房间事件进消息列表（系统消息），房主能看见门口被挡的记录。
4. 三处显示同口径；前端改动极小（一处文案 + 一个徽标）。
5. 顺带修：列表排序补 `id` 兜底（分页不再重叠）；时间列默认改语句级 `clock_timestamp()`（同事务多行排序不再随机，迁移 005 + 守卫用例）。
6. 文档：ADR-0016 + 实现页 + 功能页 + 使用者教学页 + 开发者 §9（含事务陷阱）。

**未闭合项 / 半成品（如实）**

| # | 项 | 状态 |
| --- | --- | --- |
| 1 | 演示库历史超容量房间（在册 > 容量） | 不自动清理，表现为「已满且暂时无人能进」；清理属运维，等你一句话 |
| 2 | 举手/焦点/共享是否也进消息列表 | 本轮不做；要加另开轮次 |
| 3 | `CAPACITY_CHECK_UNAVAILABLE`（外部校验失败语义） | 未引入（库内判定不会失败）；若将来重新引入外部判定必须 fail-closed |
| 4 | 前端「已满」的文案/位置若要改（例如按钮置灰而不是徽标） | 属界面口径，随时可改 |

## 6. 合并指引（由人执行）

```bash
git checkout main
git merge --no-ff req/r005-fix-capacity
git tag -a round-r005-done -m "r005 完成（容量按在册成员 + 房间事件系统消息 + 取票提速）"
```

合并后复验：`pytest backend/tests -q` → `python backend/scripts/smoke.py` → `cd frontend && npx tsc --noEmit && npm run build`。
