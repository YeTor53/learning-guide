---
title: r005 变更台账（容量口径 + 系统消息）
description: cp 台账、文件 × 模块 × 文档锚点、证据分节与用户消息台账。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
证据与用户原话按 §2 分节累积；收官时与 `git log` 互核。

## 1. cp 台账

| cp | 内容 | 状态 | 提交 SHA | 证据 |
| --- | --- | --- | --- | --- |
| cp-r005-0 | 阶段 1 文档先行（需求单 + design + ADR-0016 + ADR-0012 指路 + 档案骨架 + 索引行） | 完成 2026-09-19 | 见本提交 | 你批「开始」（Q1~Q5 = 2 / 2 1 / 1 1） |
| cp-r005-1 | 后端口径：申请/批准按在册封顶（原子）+ 取票去掉 LiveKit 查询 + 并发不变量用例 | **完成 2026-09-19** | 见本轮 cp-1 提交 | `pytest` **106 passed**（含新并发用例；旧两条「不校验容量」用例已按 ADR-0016 翻转） |
| cp-r005-2 | 系统消息：六类房间事件写 `kind='system'`（同事务）+ 用例 | planned | — | E5 |
| cp-r005-3 | 前端：状态条「在册 N / 容量」+ 列表卡满员态 + 真机截图 | planned | — | E1/E7 |
| cp-r005-4 | 收官：smoke 补步骤、教学页/功能页/实现页、review 定稿 | planned | — | E6/E8 |

## 2. 文件 × 模块 × 文档锚点

| 文件 | 模块 | 改什么 | 落的文档锚点 | 状态 |
| --- | --- | --- | --- | --- |
| `docs/00-requirements/r005-fix-capacity.md` | 契约 | 需求/口径/验收/覆盖矩阵 | 自身 | landed（cp-0） |
| `docs/rounds/r005-fix-capacity/design.md` | 契约 | 函数级设计/系统消息/契约面 | 自身 | landed（cp-0） |
| `docs/03-decisions/r005-adr-0016-room-capacity-membership.md` | 决策 | 容量权威 = 在册 | 自身 | landed（cp-0） |
| `backend/app/services/rooms.py` | 后端 | 申请/批准封顶（原子）、取票去外部调用；系统消息见 cp-2 | design §3/§4 | landed（cp-1） |
| `backend/app/repositories/rooms.py` | 后端 | 三处列表排序加 `id` 兜底（决定性排序，修分页重叠） | design §10 | landed（cp-1） |
| `backend/tests/test_rooms_service.py`、`test_rooms_members_api.py`、`test_rooms_concurrency.py` | 测试 | 两条旧口径用例按 ADR-0016 翻转 + 新增「一个名额并发批准」用例 | design §8 E2/E3 | landed（cp-1） |
| `backend/app/repositories/rooms.py` | 后端 | `insert_system_message` | design §3 | planned（cp-2） |
| `frontend/src/pages/RoomLivePage.tsx`、`components/RoomCard.tsx` | 前端 | 状态条文案、满员态 | design §5 | planned（cp-3） |
| `backend/tests/test_room_capacity.py`（新） | 测试 | E2/E3/E4/E5 用例 | design §8 | planned（cp-1/2） |
| `backend/scripts/smoke.py` | 工具 | 容量与系统消息步骤 | design §8 | planned（cp-4） |

## 3. 用户消息台账（首行回执的核对凭据）

| # | 日期 | 用户原话（摘要） | 回执分类 | 落点 |
| --- | --- | --- | --- | --- |
| 1 | 2026-09-19 | 「还有房间人数在外面显示 8/8 你跟我说应该能进？毛病？按真实房间人数限制实现，抓紧项目，其他别管了，需求确认」 | 重定向 · r004-02 | `docs/rounds/r004-room-extras/redirect-02.md` |
| 2 | 2026-09-19 | 「2 不要以 livekit 为准…2 1 但是留一个消息，这种房间事件都可以进消息列表，1 1，开始」 | 批复（Q1~Q5）+ 开工 | 本表 §1 cp-0、需求单 §3 |

## 4. 证据（按 cp 分节）

### 4.1 cp-0（阶段 1）
- 需求单/design/ADR-0016 落盘；ADR-0012 追加 D9 指路行（正文不改）。

### 4.2 cp-1（后端口径）
- `pytest backend/tests -q` → **106 passed**（原 105；两条旧口径用例翻转后净 +1）。
- 用例翻转（依据 ADR-0016，属已批准契约变更）：`test_request_join_allowed_when_full` → `test_request_join_rejected_when_full`（409 `ROOM_FULL` 且不落 pending）；`test_approve_allowed_when_full` → `test_approve_rejected_when_full`（409 且保持 pending、在册数不变）；接口层 `test_capacity_is_enforced_at_token_time_with_presence` → `test_capacity_is_enforced_by_membership`（满员拒申请 + **把 `list_participant_identities` 打成会抛错**仍能取票 → 证明取票不再依赖 LiveKit）。
- 新增并发用例 `test_concurrent_approve_respects_capacity`：capacity=3、在册 2、两条待批 → 并发批准只过一个（`["ROOM_FULL","ok"]`），且最终在册 ≤ 容量。
- 顺带修（L1，无对外面变化）：`repositories/rooms.py` 三处列表排序加 `r.id`/`m.id` 兜底 —— 修掉「同一秒建的房间分页会重叠」的潜在缺陷（`test_list_rooms_pagination` 曾因演示库时间戳打平而失败）。
