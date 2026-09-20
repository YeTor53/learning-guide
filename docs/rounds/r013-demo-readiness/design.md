---
title: r013 设计：演示就绪五项（焦点修复 / 强停共享 / worker 自愈 / 结束房回看 / 大屏进抽屉）
description: 逐文件函数级设计——三人档焦点三处判定与修法路径、共享强停的客户端事件处理与取证口径、worker 连接重试与错误透出、结束房只读回看页的数据来源与权限、大屏面板组件拆分与抽屉第四 tab；含契约面、失败边界、回退与视觉契约。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-20
---

<!-- overview -->
事实源：`docs/00-requirements/r013-demo-readiness.md`（范围与验收 E1~E12）、`docs/rounds/r009-focus-system/design.md`（舞台几何）、`docs/rounds/r004-room-extras/design.md`（共享与广播）、`docs/rounds/r010-transcription/design.md`（worker 与转写）、`docs/rounds/r012-superadmin-console/design.md`（大屏）。

## 1. A 三人档焦点（文件级）

现状链路（读码结论）：点击举手格「给焦点」→ `RoomLivePage.grantFocusFromHand(identity)` → `focus.setFocus(identity)`（`useRoomFocus`，HTTP + DataChannel 广播）→ `LiveStage` 收到 `focusUserId` → 布局条件：
1. `focusMemberActive = focusUserId && members.some(m => m.userId === focusUserId && m.status === 'active')`（`LiveStage.tsx`）；
2. `geometry.focusIdentity = screenOwnerId ?? (focusMemberActive ? focusUserId : null)`；
3. `computeStageGeometry` 内 `focused = identities.includes(focusIdentity) ? focusIdentity : null`，`identities` 来自 `useTracks(...)`（有轨道的参与者，已剔 agent 与超管）。

**修法（两条路径，复现后择一）**
- **路径 A（判据放宽）**：把「焦点是否生效」从「名册 `status==='active'`」改为「**该 identity 在舞台 identities 里**」——名册是库里的成员身份（房间结束后 `inactive`、刚进房时可能未刷新），而舞台身份是 LiveKit 在场事实（ADR-0011 口径）。实现：`LiveStage` 里删掉 `focusMemberActive` 的名册依赖，改为
  ```ts
  const focusInStage = focusUserId ? ordered.includes(focusUserId) : false
  ```
  并在 `ordered` 之后再算 `geometry`（顺序调整：先把 `focusUserId` 塞进排序 rank，再判在场）。
- **路径 B（时序等待）**：若复现显示是「焦点先于轨道就位」的时序问题，则保留名册判据但加**在场兜底**：`focusMemberActive || focusInStage`。

新增文件：`frontend/scripts/verify-focus-three-way.py`
```python
# 三个隔离 Chrome（host / m2 / m3），同一房间
async def main(base, ports, keep_chrome) -> int
async def join_room(page, base, room_id, room_title) -> None      # 登录 + 进房 + 等「已连接」
async def grant_focus_from_hand(host, target_name) -> bool        # 抽屉成员 tab → 目标行「给焦点」
def stage_state(probe: dict) -> dict                             # {"mode":…, "focusCells":…, "ids":[…]}
async def assert_three_ends(host, m2, m3, target) -> list[tuple]  # E1/E2 判据
```

## 2. B 服务端强停共享（文件级）

现状：`useScreenShare.findScreenShareOwner(room)` 扫本地与远端 `trackPublications` 里 `ScreenShare && !isMuted`；`scan()` 挂在 `LocalTrackPublished/Unpublished`、`TrackPublished/Unpublished`、`TrackMuted/Unmuted`、`ParticipantDisconnected`、`Connected` 上。
**预期**：共享者关标签 → LiveKit 判其离线 → 对端收到 `ParticipantDisconnected` → `scan()` → `ownerId=null` → 共享格消失。
**取证脚本**：`frontend/scripts/verify-screen-force-stop.py`
- 起两个隔离 Chrome（A 共享 / B 观看）→ A 点「共享屏幕」（无头需 `--auto-select-desktop-capture-source` 或用 `--use-fake-ui-for-media-stream`+`getDisplayMedia` 桩；若两者都不通，则退化为「A 用 CDP `Page.navigate('about:blank')` 强断」并明确记录手段等级）；
- 记录 `t0 = 关闭 A 的时刻`，B 端每 500ms 检查 `document.querySelectorAll('.live-cell.is-share').length`，首次归零记 `Δt`；
- 输出：`Δt`、B 端是否出现过「停在最后一帧」（共享格存在但视频冻结）、A 端离线判定的秒数。
**修法（仅当 Δt > 10 秒或不清格）**：候选 `ParticipantDisconnected` 后加 `setTimeout(recheck, 3000)` 兜底重扫；或对 `TrackUnpublished` 增加 `isMuted` 变化监听（已含）。**不改协议。**

## 3. C 转写 worker 自愈与可观测（文件级）

`backend/agents/transcriber.py`：
```python
async def _connect_with_retry(ctx: JobContext, attempts: int = 3, backoff: Sequence[float] = (2.0, 4.0)) -> None:
    """ctx.connect() 有限重试；每次失败记 warning（含 attempt/异常类型）；全部失败抛最后一次异常。"""

def _post_heartbeat_sync(room_id: str, sessions: int, last_error: str | None = None) -> None:
    """（改）请求体加可选 lastError；失败仍只记 debug。"""

async def _heartbeat_loop(room_id: str, pool: TranscriberPool, last_error: Callable[[], str | None]) -> None:
    """（改）每 HEARTBEAT_SECONDS 上报；把 last_error() 的结果带上。"""

@server.rtc_session(agent_name=AGENT_NAME)
async def entrypoint(ctx: JobContext) -> None:
    """（改）连接段包 try：失败 → 结构化日志 + 退出码 2（交 agents.bat/守护重启），不再裸崩在 FFI。"""
```
`backend/app/schemas/transcripts.py`：`class SttHeartbeatIn` 加 `last_error: Optional[str] = Field(default=None, alias="lastError")`（长度上限 200）。
`backend/app/services/stt.py`：`record_heartbeat(..., last_error: str | None = None)` 保存进内存态；`latest_heartbeat()` 返回值加 `lastError`。
`backend/app/api/routers/transcripts.py`：`post_stt_heartbeat` 透传 `payload.last_error`；`read_stt_status`（`GET /api/stt/status`）与**按房状态**端点（`GET /api/rooms/{id}/stt-status`）都返回 `lastError`。
前端：`api/transcripts.ts` 的 `RoomSttStatus` 加 `lastError: string | null`；`RoomLivePage` 转写芯片加 `title`（`最后错误：<截 80 字>`），无错误时不显示。

## 4. D 结束房只读回看页（文件级）

数据来源（全部复用既有端点，**不加新接口**）：
- `GET /api/rooms/{id}` → `services/rooms.py::get_room_detail`（ended 房 `include_inactive=True`，成员含加入/离开时间与退出原因）；
- `GET /api/rooms/{id}/conversation?limit=200` → `services/transcripts.py::build_conversation`（聊天 + 系统消息 + 转写三源合一，正序）；
- `GET /api/rooms/{id}/summary` → 纪要（`session_summaries`）。

**权限口径（默认 §10 Q1=1，实现点）**：`services/rooms.py` 新增
```python
def assert_can_replay(conn: Connection, actor: Optional[UserVO], room_id: str) -> RoomRow:
    """回看可见性：房主 / 历史协管 / 超管 / **当时在册成员**（含已 inactive）；其余 403。"""
```
并在 `routers/rooms.py` 的详情 / `transcripts.py` 的 conversation / `summary.py` 的读取三处，凡 `room.status == 'ended'` 时改走该判据（保住「普通人回看自己参与过的房」）。**未结束的房间行为不变。**

前端：
- 新页 `frontend/src/pages/ReplayPage.tsx`（只读三段 + 顶部房头 + 「返回房间列表」）；
- 新 hook `frontend/src/hooks/useReplay.ts`：`useReplay(roomId)` → `{ room, timeline, summary, error, loading }`（并发取三接口，任一 403 → `forbidden=true`）；
- `components/RoomCard.tsx`：`room.status === 'ended'` 时把「回到讨论」换成「回看」→ `navigate('/rooms/{id}/replay')`；
- `App.tsx` 路由：`<Route path="/rooms/:id/replay" element={<ReplayPage />} />`。

## 5. E 大屏并入交流页抽屉（文件级）

拆分：把 `components/GlobalChatDrawer.tsx` 里的**面板内容**抽成 `components/GlobalChatPanel.tsx`
```tsx
export interface GlobalChatPanelProps { open: boolean; onClose?: () => void; variant?: 'drawer' | 'embedded' }
export default function GlobalChatPanel({ open, onClose, variant = 'drawer' }: GlobalChatPanelProps)
```
- `GlobalChatDrawer` 保留外层 `aside.gc-drawer` 与开合/宽度/Esc 逻辑，内部渲染 `<GlobalChatPanel variant="drawer" />`（**行为与类名不变**，三份自检脚本仍可用）；
- `components/live/RoomSidePanel.tsx`：`type Tab = 'chat' | 'members' | 'invite'` 扩为 `| 'global'`，第四个 tab 文案「大屏」，渲染 `<GlobalChatPanel variant="embedded" open />`；
- `RoomLivePage.tsx`：把 `roomId / myUserId` 之外的 `globalChat` 状态（`useGlobalChat()`）透传给 `RoomSidePanel`；顶栏大屏按钮在交流页继续不渲染（`App.tsx` 现状保留）；
- 未读徽标：仍只算讨论消息（不变）。

## 6. 契约面（前后端共享的口径）

| 契约 | 形状 | 变更 |
| --- | --- | --- |
| `SttHeartbeatIn` | `{roomId, sessions, lastError?}` | 加 `lastError`（可选，向后兼容：不带 = null） |
| `/api/rooms/{id}/stt-status` | `{..., lastError}` | 加字段 |
| ended 房读权限 | 房主/历史协管/超管/在册成员 | **放宽一档**（Q1） |
| 回看页路由 | `/rooms/:id/replay` | 新增 |
| 抽屉 tab | `chat / members / invite / global` | 新增第 4 个 |

## 7. 失败与边界

1. 焦点：若目标 `identity` 与 `userId` 不一致（超管、agent 已排除）——按 identity 匹配，不引入新的不一致。
2. 强停共享：若 LiveKit 判离线 > 10 秒，如实记数（B 项判据只要求记录）。
3. worker：重试期间房间内该参与者无转写 → 前端芯片显示「未开启」+ hover 显示最后错误；不假装在转。
4. 回看页：三接口任一失败 → 分区级降级（其余照常渲染），不整页白屏。
5. 大屏 embedded 变体：不开新 `EventSource`（复用 `useGlobalChat` 的单例连接），避免「开两个面板两条流」。

## 8. 回退

每项独立成 cp，回退 = `git revert <cp 提交>`；无迁移、无数据变更，回退无副作用。E 项拆分保留 `GlobalChatDrawer` 外壳，回退只需还原 `RoomSidePanel` 与 `RoomLivePage` 两处调用。

## 9. 视觉契约

沿用既有令牌与组件（无新颜色）：回看页用 `.panel/.card` 既有类；时间线复用 `ChatPanel` 的行样式但**只读**（不渲染输入区）；大屏 embedded 去掉抽屉投影与宽度，占满 tab 内容区；worker 错误只出现在 `title`，不新增常驻文案（沿用「引导靠入口、不靠解释文字」口径）。

## 10. 变更记录

| 日期 | 版本 | 变更 | 依据 |
| --- | --- | --- | --- |
| 2026-09-20 | v1 | 建页：A~E 五项逐文件函数级设计 + 契约面 + 失败边界 + 回退 + 视觉契约 | 需求单 v1；你「把到 6 的都做了」 |
