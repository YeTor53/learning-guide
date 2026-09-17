---
title: r001 房间 M2/M3 能力设计预告（已归档）
description: 从 r001 房间设计页剥离的 M2/M3 内容：邀请、踢人、角色任命、Host 移交与 LiveKit 接入。
type: reference
status: backlog
owner: 陀梓皓
updated: 2026-09-17
---

<!-- overview -->
> ⚠ **已归档（2026-09-17）**：按 `global-roadmap.md` §8.3 方案 B，把**超出 r001（M1）范围**的房间能力从 r001 页剥离到本页，标 `status: backlog`。
> **不是本轮方案**；M2/M3 立轮次时按该轮号改名并移回 `docs/02-modules/`。
> 房间的 M1 内容见 `docs/02-modules/r001-rooms.md`；功能层描述见 `docs/02-modules/r001-rooms-features.md`；LiveKit 来源决策见 `docs/03-decisions/r001-adr-0003-livekit-source-review.md`。

## 1. 剥离清单

- 邀请（`invites` 表、生成/兑换、TTL 与使用上限、邀请绕过与否）
- 踢人（服务端强制断开）、角色任命、Host 移交
- LiveKit 接入模块（签 Token、移除参与者、删除房间、在场列表）与踢人后的 Token 失效分支

## 2. 被剥离的行（原 r001 页片段的原始内容）

| 建邀请 | Host/Moderator | 房间 `active`；TTL ∈ [5, 1440] 分钟 | 写 `invites`（`code` 6 位、`expires_at`、`max_uses`） | `FORBIDDEN` / `ROOM_ENDED` |
| 用邀请 | 登录用户 | 邀请未过期、`used_count < max_uses`、房间 `active`、非活跃成员 | `used_count += 1` + 写成员（或直接进入申请流程，见 R-2） | `INVITE_INVALID` / `ROOM_ENDED` / `ALREADY_MEMBER` |
| 踢人（M2） | Host/Moderator | 目标为活跃成员且非 Host | 成员置 `inactive/kicked`；事务提交后调 LiveKit 移除参与者 | `FORBIDDEN` / `NOT_MEMBER` / `ROOM_ENDED` |
| 改角色（M2） | Host | 目标为活跃成员 | 更新 `role`（`participant↔moderator`） | `FORBIDDEN` |
| 移交 Host（M2） | Host | 目标为活跃成员 | 双方 `role` 互换（Host ↔ Moderator/Participant） | `FORBIDDEN` |
| POST | `/api/rooms/{room_id}/invites` | Host/Moderator | `{ttlMinutes, maxUses?}` | 201 `{code, expiresAt, url}` （M2） |
| POST | `/api/invites/{code}/redeem` | 登录 | — | 200 `{room, member}` 或 202 `{request}` （M2，形态见 R-2） |
| POST | `/api/rooms/{room_id}/members/{user_id}/kick` | Host/Moderator | — | 200 `{}` （M2） |
| PATCH | `/api/rooms/{room_id}/members/{user_id}` | Host | `{role}` | 200 `MemberVO` （M2） |
| POST | `/api/rooms/{room_id}/transfer-host` | Host | `{userId}` | 200 `{members}` （M2，见 R-4） |
| `update_member_role` | `(conn, room_id: str, user_id: str, role: str) -> None` | 改角色/移交 |
| `insert_invite` | `(conn, row: NewInvite) -> None` | 写邀请 |
| `get_invite_by_code` | `(conn, code: str) -> InviteRow \| None` | 校验邀请 |
| `bump_invite_used` | `(conn, invite_id: str) -> int` | `used_count += 1`（`WHERE used_count < max_uses`，返回受影响行数，0 表示已用尽） |
| `create_invite` | `(conn, actor: User, room_id: str, ttl_minutes: int, max_uses: int) -> InviteVO` | `assert_room_role(host, moderator)` → 写邀请 |
| `redeem_invite` | `(conn, actor: User, code: str) -> RedeemResult` | 校验未过期/未用尽/房间 `active`/非成员 → 形态见 R-2 |
| `kick_member` | `(conn, actor: User, room_id: str, user_id: str) -> None` | `lock_room` → `assert_room_role(host, moderator)` → 目标活跃且非 Host → `deactivate_member(kicked)` → 提交后 `livekit.remove_participant` （M2） |
| `set_member_role` | `(conn, actor: User, room_id: str, user_id: str, role: str) -> MemberVO` | `assert_room_role(host)` → 目标活跃 → 改角色（M2） |
| `transfer_host` | `(conn, actor: User, room_id: str, user_id: str) -> list[MemberVO]` | `assert_room_role(host)` → 双方角色互换（M2） |
### 6.5 `app/services/livekit.py`（M2 用；签名与分支先定）

| 函数 | 签名 | 职责 / 返回 |
| --- | --- | --- |
| `issue_token` | `(room_id: str, user: User, role: str, ttl_seconds: int = 3600) -> str` | 用 `AccessToken(...).with_identity(user.id).with_name(user.display_name).with_grants(VideoGrants(room_join=True, room=room_id, can_publish=True, can_publish_data=True, room_admin=(role=='host')))` + `with_room_config(RoomConfiguration(max_participants=8))` 签 JWT；**Secret 只在此模块读环境变量** |
| `remove_participant` | `(room_id: str, user_id: str, revoke: bool = True) -> None` | 调 `LiveKitAPI.room.remove_participant`；**分支（P3′）**：Cloud 传 `revoke_token_ts=now` 使已签发 Token 立即失效；自建下该字段无同等效果 → 依赖 `issue_token` 的短 TTL（建议 5 分钟）+ 拒绝再签发（见 §10） |
| `delete_room` | `(room_id: str) -> None` | 房间结束时强制断开全部连接（`room.delete_room`） |
| `list_participants` | `(room_id: str) -> list[str]` | 房间内在场的 identity 列表（派生相位 `in_session` 与演示取证） |

| `InviteIn` | `ttl_minutes: int`, `max_uses: int = 8` | TTL ∈ [5,1440] |
| `RoleIn` | `role: Literal["moderator","participant"]` | 改角色 |
| `routers/rooms.py` | `list_rooms`, `create_room`, `get_room`, `create_join_request`, `list_join_requests`, `approve_request`, `reject_request`, `leave_room`, `end_room`, `create_invite`, `redeem_invite`, `kick_member`, `patch_member`, `transfer_host` | 每个 5–15 行：取依赖 → 调 service → `to_response`；异常由全局 handler 统一转信封 |
| 邀请过期 / 用尽 | `expires_at < now()` 或用尽 → `INVITE_INVALID`；房间 `ended` 时邀请一律 `ROOM_ENDED`（不删邀请行） |
| 外部服务失败（M2 的 `delete_room`） | 数据库事务已提交，失败只记日志；房间状态不受影响（房间结束是用户意图） |
| B1 | 踢人后的 Token 失效方式 | Cloud：`revoke_token_ts` 立即失效 / 自建：短 TTL（5 分钟）+ 拒绝再签发 | 随 P3′ 定 | P3′ |
| R-2 | 用邀请的落点 | ① 直接成为成员 ② 仍走等候室申请 | ②（与题面「进入房间前需经过等候室」一致） | 影响 M2 流程 |
| R-3 | 被踢过的人能否再申请 | 允许（记 `kicked` 历史）/ 设冷静期 | 允许 | 影响规则表 |
| R-4 | Host 移交 | 做（本文已给签名）/ 不做（Host 只能结束房间） | 做，归 M2 | 影响 M2 工作量 |

## 3. 功能层剥离内容（原 r001 功能页片段）

### F-06 生成邀请（M2）

- **入口**：详情页「邀请」按钮（Host/Moderator）。
- **可设置项**：有效期（5 / 30 / 60 / 1440 分钟，默认 30）、使用上限（默认 8）。
- **产物**：6 位房间码（剔除易混字符）与可复制链接；弹窗内文案「此邀请 30 分钟后失效，最多可用 8 次」。
- **规则**：房间 `ended` 后邀请立即失效（即使未到过期时间）；已过期或用尽的邀请提示「邀请已过期，请向房主索取新的邀请链接」。
- **验收点**：改系统时间/等待过期后再用 → 提示过期；房间结束后用同一链接 → 提示房间已结束。


### F-07 用邀请加入（M2）

- **入口**：邀请链接直接打开房间详情页并弹出「通过邀请加入」；或在列表页「输入房间码」。
- **流程**：点「通过邀请加入」→ 仍进入等候室（提交申请，标注「凭邀请」）→ 房主批准后进入正式讨论。理由：题面要求「进入房间前需经过等候室：房主批准后才能进入正式讨论」，邀请只降低找房间成本，不绕过审批。
- **提示**：邀请无效/过期/用尽 → 对应提示且不提交申请。


### F-10 踢出成员（M2）

- **入口**：成员列表行内「移出房间」（Host/Moderator）。
- **限制**：不能踢房主；协管不能踢协管（仅房主可）；不能踢自己（自己用「离开房间」）。
- **行为**：确认后该成员被移出：成员列表标记「被移出」；对方连接被服务端强制断开并显示「你已被移出房间」（非前端假踢）；被移出者可再次提交申请（是否设冷静期见 FQ-3）。
- **提示**：权限不足 → 「没有权限执行该操作」。


### F-11 任命协管 / 移交房主（M2）

- **任命协管**：房主在成员行内选「设为协管 / 取消协管」；协管获得处理申请、生成邀请、踢人（除协管互踢）的能力。
- **移交房主**：房主选「移交房主」→ 二次确认（「移交后你将变为协管，且不能再收回」）→ 双方角色互换，对方成为房主。
- **验收点**：角色变化立即反映在双方页面的按钮可见性上。


| 邀请过期 | 邀请已过期，请向房主索取新的邀请链接 |
| 被移出房间 | 你已被移出房间 |
| FQ-3 | 被移出者再申请 | 立即允许（本文按此）/ 设冷静期 | 立即允许 |
| FQ-6 | 邀请是否可绕过等候室 | 不绕过（本文按此）/ 直进房间 | 不绕过 |
