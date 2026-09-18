---
title: r002 邀请能力设计（延后 · backlog）
description: 从 r001 归档页抽出的「生成邀请 / 用邀请加入」设计片段，本轮（r002）不做，留作后续轮次的输入。
type: reference
status: backlog
owner: 陀梓皓
updated: 2026-09-18
---

<!-- overview -->
> ⚠ **不是本轮方案**（2026-09-18 归档）：r002 只做 M2 的实时房间/权限/等候室，**邀请不在本轮范围**（依据见 `docs/00-requirements/r002-livekit-room.md` §3 的 Q1）。
> 本页保存该能力的既有设计片段（接口、规则、功能描述、函数签名），开轮次时移回 `docs/02-modules/` 并按该轮号改前缀。
> 相关：踢人/角色任命/移交已在 r002 落地，见 `docs/02-modules/r002-livekit.md` 与 `r002-livekit-features.md`；数据表 `invites` 已建但本轮不使用（见 `docs/02-modules/r001-rooms.md` §3）。

## 1. 数据与规则（原归档页片段）

`invites` 表（r001 已建）：`id / room_id / code(6 位唯一) / created_by / expires_at / max_uses(1..8) / used_count / created_at`。

| 操作 | 触发者 | 前置 | 副作用 | 错误码 |
| --- | --- | --- | --- | --- |
| 建邀请 | Host/Moderator | 房间 `active`；TTL ∈ [5, 1440] 分钟 | 写 `invites`（`code` 6 位、`expires_at`、`max_uses`） | `FORBIDDEN` / `ROOM_ENDED` |
| 用邀请 | 登录用户 | 邀请未过期、`used_count < max_uses`、房间 `active`、非活跃成员 | `used_count += 1` + 写成员（或进入申请流程，见下 R-2） | `INVITE_INVALID` / `ROOM_ENDED` / `ALREADY_MEMBER` |

## 2. 接口与签名（原归档页 §2 片段）

| 方法 | 路径 | 谁能调 | 请求 / 响应 |
| --- | --- | --- | --- |
| POST | `/api/rooms/{room_id}/invites` | Host/Moderator | `{ttlMinutes, maxUses?}` → 201 `{code, expiresAt, url}` |
| POST | `/api/invites/{code}/redeem` | 登录 | — → 200 `{room, member}` 或 202 `{request}`（形态见 R-2） |

| 函数 | 签名 | 职责 |
| --- | --- | --- |
| `insert_invite` | `(conn, row: NewInvite) -> None` | 写邀请 |
| `get_invite_by_code` | `(conn, code: str) -> InviteRow \| None` | 校验邀请 |
| `bump_invite_used` | `(conn, invite_id: str) -> int` | `used_count += 1`（`WHERE used_count < max_uses`，返回受影响行数，0 表示已用尽） |
| `create_invite` | `(conn, actor: User, room_id: str, ttl_minutes: int, max_uses: int) -> InviteVO` | `assert_room_role(host, moderator)` → 写邀请 |
| `redeem_invite` | `(conn, actor: User, code: str) -> RedeemResult` | 校验未过期/未用尽/房间 `active`/非成员 |

## 3. 功能描述（原归档页功能片段）

### F-06 生成邀请

- **入口**：详情页「邀请」按钮（Host/Moderator）。
- **可设置项**：有效期（5 / 30 / 60 / 1440 分钟，默认 30）、使用上限（默认 8）。
- **产物**：6 位邀请码（剔除易混字符）与可复制链接；弹窗文案「此邀请 30 分钟后失效，最多可用 8 次」。
- **规则**：房间 `ended` 后邀请立即失效（即使未到过期时间）；已过期或用尽的邀请提示「邀请已过期，请向房主索取新的邀请链接」。
- **验收点**：等待/调时间过期后再用 → 提示过期；房间结束后用同一链接 → 提示房间已结束。

### F-07 用邀请加入

- **入口**：邀请链接直接打开房间详情页并弹出「通过邀请加入」；或列表页「输入房间码」。
- **流程**：点「通过邀请加入」→ 仍进等候室（提交申请，标注「凭邀请」）→ 房主批准后进入正式讨论。理由：交付要求「进入房间前需经过等候室」，邀请只降低找房间成本，不绕过审批。
- **提示**：邀请无效/过期/用尽 → 对应提示且不提交申请。

## 4. 待拍板（开轮次时复核）

| 编号 | 事项 | 选项 | 建议 |
| --- | --- | --- | --- |
| R-2 | 用邀请的落点 | ① 直接成为成员 ② 仍走等候室申请 | ②（与「进门需过等候室」一致） |
| FQ-3 | 被移出者再申请 | 立即允许 / 设冷静期 | 立即允许（r002 已按此落地） |
| FQ-6 | 邀请是否可绕过等候室 | 不绕过 / 直进房间 | 不绕过 |

## 变更记录

- 2026-09-18 建立：内容取自 r001 的 M2/M3 归档页（该文件已随 r002 移回 `docs/02-modules/` 并改写）；标 `status: backlog`，不阻塞 r002~M4。
