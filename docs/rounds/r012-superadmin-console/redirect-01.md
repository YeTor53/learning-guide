---
title: r012 登记 01：超管用户 + 简单管理后台 + 全服大屏聊天
description: 你 2026-09-20 口述的超管需求读back、与既有容量/在册口径的冲突点、数据模型草案与待拍板 Q1~Q8。
type: reference
status: proposed
owner: 陀梓皓
updated: 2026-09-20
---

<!-- overview -->
来源：你 2026-09-20「记下 r012 将这方面的管理也记账，设计超管用户，超管负责管理所有房间，包括先前的简单管理能力，任一房间的房主的管理能力，进入任何房间的能力（包括满人，不计入人数，但不会显示，进入，不会出现头像在聊天栏或占用焦点空间，只在进行管理行为的时候在房间聊天栏产生消息，可以在大屏发言）」。
外加同批已定的：**简单管理后台**（题目加分项「简单管理后台（房间/用户/纪要列表）」）与**全服大屏聊天**（参数见 §4）。**本单未批前不动代码**；r011 收工后再开本轮。

## 1. 读back（请纠错）

1. **超管是独立身份**：能进任何房间（含满员），能行使**任一房间房主**的全部管理动作，另有**跨房**的管理能力（原「简单管理后台」）。
2. **隐身**：进入房间时**不出现在成员列表**、**不占舞台/焦点格**、**不显示头像**。
3. **不计入人数**：超管在场不影响房间的容量判定（在册数、满员判定）。
4. **只在管理动作时留痕**：超管在房间聊天栏**只**在它执行管理行为时产生消息；平时不说话不留痕。
5. **可以发言**：能在「大屏」发言（口径待你确认，见 Q4）。
6. r012 还包含：简单管理后台（房间 / 用户 / 纪要列表）+ 全服大屏聊天。

## 2. 与既有口径的冲突点（先摊开）

| # | 冲突 | 说明 |
| --- | --- | --- |
| 1 | 容量口径 | r005/ADR-0016 定「容量按**在本库在册成员数**」；超管「不计入人数」要求它在册但不算数 → 必须明确是「不进 `room_members`」还是「进但被排除计数」 |
| 2 | 「隐身」与「在册」 | 现口径「在册才能取票、才能发言、才能看房间内容」；超管两样都要（能看能操作）但不能出现在成员列表 |
| 3 | 转写与纪要 | 超管在房间里的音频/发言是否进转写与纪要？（现状：房间侧 worker 给**每个有音频轨的人**开会话） |
| 4 | 「不显示头像」 vs 「可以在大屏发言」 | 若发言要出现在舞台/聊天，就必然有某种身份露出；两者需要你定优先级 |
| 5 | 全服聊天的「在线」 | 你在 r011 redirect-01 里批过「在线 = 心跳 60 秒内」，需要 `users.last_seen_at`（或在线表） |

## 3. 数据模型草案（待你定后再出函数级设计）

```sql
-- Q1 定身份来源后二选一
-- ① users 加列（推荐）
ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'
  CHECK (role IN ('user','superadmin'));
-- ② 或独立表 super_admins(user_id ...)

-- Q2 定「不计入人数」后二选一
-- A 方案：超管不写 room_members，进出记独立表
CREATE TABLE room_visits (id TEXT PRIMARY KEY, room_id TEXT REFERENCES rooms(id),
  user_id TEXT REFERENCES users(id), entered_at TIMESTAMPTZ DEFAULT clock_timestamp(),
  left_at TIMESTAMPTZ, hidden BOOLEAN NOT NULL DEFAULT true);
-- B 方案：写 room_members 但计数排除
--   count_active_members(...) 加 `AND role <> 'superadmin'`，成员列表查询同样过滤

-- 全服大屏聊天（新表，不复用 room_id NOT NULL 的 chat_messages）
CREATE TABLE global_messages (id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
  body TEXT NOT NULL CHECK (char_length(body) BETWEEN 1 AND 500),
  created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp());
CREATE INDEX ix_global_messages_time ON global_messages (created_at DESC);

-- 在线口径（二选一：方案 A 简单）
ALTER TABLE users ADD COLUMN last_seen_at TIMESTAMPTZ;

-- 后台操作留痕
CREATE TABLE admin_audit (id TEXT PRIMARY KEY, actor_id TEXT REFERENCES users(id),
  action TEXT NOT NULL, target TEXT NOT NULL, detail JSONB, created_at TIMESTAMPTZ DEFAULT clock_timestamp());
```

## 4. 已定参数（沿用你先前批复，不改）

- 全服大屏聊天：只显示**在线**用户消息；常规页面里的一个宽聊天面板（不做独立投屏页）；登录用户可看可评、未登录只看；全量落库 + 每人限流 + 单条 500 字；实时通道沿用**SSE** 口径（`GET /api/events` 只推通知型事件，HTTP 落库仍是唯一真相），断线用短轮询兜底。
- 好友 / 定向邀请那套（原 r011 redirect-01 的 Q1~Q8）：**作废**，只保留其中 SSE 口径备用。

## 5. 待拍板（回数字；例 `1 1 1 1 1 1 1 1`）

| # | 问题 | 选项 | 建议 |
| --- | --- | --- | --- |
| Q1 | 超管身份怎么来 | ① `users.role` 加列（迁移）② 独立表 `super_admins` ③ `.env` 白名单邮箱（零迁移） | ① |
| Q2 | 「不计入人数」实现 | ① 超管不写 `room_members`，进出记 `room_visits`（天然隐身、天然不计数）② 写 `room_members` 但计数与列表统一排除 `superadmin` | ①（干净，但取票路径要单独分支） |
| Q3 | 「不显示」的边界 | ① 成员列表/舞台格/在线口径都不出现，管理动作产生的消息署名「超管」② 连消息也不署名（显示为系统消息）③ 房主/协管能看到「有超管在场」的小标记 | ① |
| Q4 | 「可以在大屏发言」指什么 | ① 指**全服大屏聊天**（r012 的公屏）能发言 ② 指房间**舞台主区**能发言（画面/声音进主区）③ 两者都要 | ①（②与「不出现头像/不占焦点」直接冲突，要的话请明确例外） |
| Q5 | 简单管理后台范围 | ① 房间/用户/纪要三个**列表** + 结束房间 / 删房间 / 重生成纪要 ② 只读列表 ③ 列表 + 完整用户管理（禁用/改角色） | ① |
| Q6 | 管理能力怎么复用 | ① 复用现有房主端点，超管绕过角色校验（改动最小）② 新增 `/admin/...` 一套端点（边界清楚、易审计） | ①（「简单做」优先），留审计见 Q7 |
| Q7 | 是否留操作审计 | ① 每条管理动作写 `admin_audit` + 房内系统消息 ② 只依赖房内系统消息 | ① |
| Q8 | 超管在房间里的音频是否进转写/纪要 | ① 不进（超管音频轨被 worker 忽略）② 进（与普通成员一致） | ①（与隐身口径一致） |

## 6. 我看到的三个风险（先说明）

1. **隐身与在册的耦合**：现实现把「在册」当作一切权限的地基（取票、发言、看内容），超管要「在册但不显现」→ 需要一条**独立的旁路校验**，改动点会散在 `services/rooms.py` 的多个 `assert_room_role` 调用处，必须一次改全，否则会出现「能进但看不到」这类半成品。
2. **容量口径的表述**：「不计入人数」必须写进 ADR（拟 ADR-0024），否则 r005 的不变量「在册 ≤ 容量」在超管在场时会被误判为破坏。
3. **全服聊天的在线口径与刷屏**：需要心跳 + 限流；免费档无影响（纯 HTTP），但要定「断线多久算离线」（建议 60 秒）。

## 7. 变更记录

| 日期 | 版本 | 改了什么 | 依据 |
| --- | --- | --- | --- |
| 2026-09-20 | redirect-01 | 建页：超管读back + 冲突点 + 数据模型草案 + Q1~Q8 + 风险；并收入同批已定的管理后台与全服大屏聊天 | 你 2026-09-20 的口述 |

## 8. 后续（2026-09-20 追加）

- 阶段 1 文档已出：需求单 `docs/00-requirements/r012-superadmin-console.md`（含界面口径卡、E1~E12、覆盖矩阵、cp 切分；Q1~Q8 原样搬入 §10 并续编 Q9~Q18）+ 设计 `design.md`（逐文件函数级）。
- 本单 §4 的「已定参数」原样沿用，未改；§5 的 Q1~Q8 未答，仍 `status: proposed`（改由 `ASK-r012-1` 统一收口）。
- 好友 / 定向邀请那套：**作废**（只保留 SSE 口径），见 `docs/rounds/r011-friends-and-invites/redirect-01.md`。
