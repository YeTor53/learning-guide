---
title: r009 函数级设计：焦点系统重做
description: 逐文件的函数签名与职责——布局算法、焦点权限流、举手闪烁、麦克风声波。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
需求与验收见 `docs/00-requirements/r009-focus-system.md`。**未批不动代码。**

## 1. 布局算法（前端唯一事实源）

### 1.1 `frontend/src/components/live/stageGeometry.ts`（**新增**，cp-1a 已落地；旧 `stageLayout.ts` 在 cp-1b 下线）

实现与本文最初草案的两处差异（**实测后改的**，见 `changes.md` §cp-1a）：

1. **焦点份量用「加权行列」而不是「跨 2 格」**：跨 2 格会让格子变成 2:1 的横条（边长 2×、面积 2×），偏离你要的「1.4 倍」。改成焦点所在**行列各乘 `FOCUS_WEIGHT=1.4`**（`distributeWeighted`）→ 面积份量稳定 1.40×，且整块区域仍是连续切分、不留洞。
2. **`bestGrid` 对空槽重罚（×2.0）**：轻罚时 3 人选 2×2（比例最正但空一格）→ 铺满率只剩 73%；重罚后 3 人 = 1×3、8 人 = 4×2，铺满率 97% / 94.6%。

签名（实际落地）：

```ts
export function bestGrid(slots, areaW, areaH, aspect?): { cols, rows }
export function distribute(areaW, areaH, cols, rows, gap): Rect[]
export function distributeWeighted(areaW, areaH, cols, rows, gap, wx?: number[], wy?: number[]): Rect[]
export function computeStageGeometry(input: StageGeometryInput): StageGeometry
export function describeGeometry(geometry): string        // 测试与日志共用
export const FOCUS_WEIGHT = 1.4
export const DEFAULT_GAP = 10
export const TARGET_ASPECT = 16 / 9
export const SHARE_STRIP_RATIO = 0.22
```

校验脚本（无需测试框架）：`node frontend/scripts/verify-stage-geometry.mjs`（esbuild 转译 → 断言 + 打印铺满率/份量/溢出）。cp-1a 实测见 `changes.md`。

### 1.1b 旧草案（保留备查）：`stageLayout.ts` 原计划

```ts
export type StageMode = 'empty' | 'uniform' | 'focus' | 'share'
export type TileKind = 'grid' | 'focus' | 'share'

export interface Rect { x: number; y: number; w: number; h: number }
export interface StageTile extends Rect { userId: string; kind: TileKind; slot: number }
export interface StageInput {
  areaW: number; areaH: number
  userIds: string[]          // 在线且已发布视频的人（音频-only 的人不占格）
  focusId?: string | null    // 手动焦点
  speakerId?: string | null  // 说话者（自动焦点）
  shareId?: string | null    // 正在共享的人
  gap?: number               // 默认令牌 --stage-gap
}
export interface StageLayout { mode: StageMode; tiles: StageTile[]; focusId: string | null }

/** 由 n 个槽位选最接近目标宽高比的列数；返回 { cols, rows }，保证 cols*rows ≥ slots 且 rows 不留空行。 */
export function bestGrid(slots: number, aspect: number): { cols: number; rows: number }

/** 把区域按 cols×rows 均分，余数像素分给靠前的行列（避免 1px 缝）；返回每格矩形。 */
export function distribute(areaW: number, areaH: number, cols: number, rows: number, gap: number): Rect[]

/**
 * 主入口（纯函数，无副作用、可单测）：
 * - shareId 存在 → mode='share'：共享格 = 顶部主区（宽 100%、高按 16:9 或剩余高的 62%），其余人像 = 底部一行小格；
 * - focusId（手动）或 speakerId（自动）存在 → mode='focus'：槽位 = n + 1，bestGrid(n+1)，
 *   焦点格占 slot0 与 slot1（同列相邻则竖向跨 2 行；否则横向跨 2 列），其余人按序填剩余槽位；
 * - 否则 mode='uniform'：槽位 = n，纯均分铺满；
 * - n=0 且无共享 → mode='empty'。
 */
export function computeStageLayout(input: StageInput): StageLayout

/** 焦点归属（保留 r004 优先级）：shareId > focusId > speakerId > localId。 */
export function resolveFocusId(input: StageInput, localId?: string | null): string | null
```

- 删除 r004 的 rail 阶梯常量（`--live-rail-*`），新增令牌：`--stage-gap: 10px`、`--focus-weight: 1.4`（记录语义：焦点跨 2 格 ≈ 1.4 倍边长）、`--tile-radius`。
- 单测（`frontend/src/lib/stageLayout.test.ts`，`node --test` + esbuild 口径沿用项目既有做法）：面积差、最优网格、焦点跨格、共享模式、n=1 铺满。

## 2. 焦点权限（后端）

### 2.1 迁移 `backend/app/db/migrations/008_r009_focus_requests.sql`

```sql
CREATE TABLE focus_requests (
  id TEXT PRIMARY KEY,
  room_id TEXT NOT NULL REFERENCES rooms(id),
  requester_id TEXT NOT NULL REFERENCES users(id),
  status TEXT NOT NULL CHECK (status IN ('pending','approved','rejected','cancelled')),
  decided_by TEXT REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  decided_at TIMESTAMPTZ
);
CREATE UNIQUE INDEX ux_focus_requests_pending ON focus_requests (room_id, requester_id) WHERE status = 'pending';
```

### 2.2 `backend/app/repositories/focus_requests.py`（新增）

```python
@dataclass(frozen=True) class NewFocusRequest: id, room_id, requester_id
@dataclass(frozen=True) class FocusRequestRow: id, room_id, requester_id, status, decided_by, created_at, decided_at

def insert_request(conn, row: NewFocusRequest) -> None
def get_pending(conn, room_id, requester_id, lock=False) -> FocusRequestRow | None
def get_by_id(conn, request_id, lock=False) -> FocusRequestRow | None
def list_pending(conn, room_id) -> list[FocusRequestRow]        # 带 requester displayName
def decide(conn, request_id, status, decided_by, decided_at) -> int
def cancel_pending_for_user(conn, room_id, user_id) -> int      # 焦点被清/用户离开时收尾
```

### 2.3 `backend/app/services/focus.py`（新增，权限都在这层）

```python
def request_focus(conn, actor: UserVO, room_id: str) -> FocusRequestVO
    """协管发起焦点申请；房主不允许走到这里（前端直接给「取得焦点」）。
       房间必须 active；已有 pending → 幂等返回同一条；返回 VO 供 SSE/DataChannel 广播。"""

def decide_focus_request(conn, actor: UserVO, request_id: str, *, approve: bool) -> FocusRequestVO
    """批准/拒绝。**必须**：actor 是 Host/Moderator 且 actor.id != requester_id（自己不能批自己，403 SELF_APPROVAL）；
       approve=True 时同事务把焦点设为申请人 + 清掉申请人举手；房间 ended → 409。"""

def grant_focus_from_hand(conn, actor: UserVO, room_id: str, user_id: str) -> FocusVO
    """管理在举手者格上点「给焦点」：设焦点 + 清该人举手（一条事务）。"""
```
- 现有 `services/room_extras.set_focus` 扩展：房主/协管直接指定他人 → 保留；**房主设自己 → 允许**（R6）；协管设自己 → 改走 `request_focus`（前端按钮分流，后端也兜底 403 提示改用申请）。
- 路由（`api/routers/room_extras.py` 追加）：
  - `POST /api/rooms/{room_id}/focus-requests` → 201
  - `GET  /api/rooms/{room_id}/focus-requests` → 200（Host/Moderator）
  - `POST /api/focus-requests/{id}/approve` / `/reject` → 200
- 错误码新增：`SELF_APPROVAL`(403)、`FOCUS_REQUEST_EXISTS`(409 可选，默认幂等)。

## 2.9 动效（见 `motion-design.md`）：`useFlipTransition(containerRef, layoutKey)` 是唯一动画实现；几何纯函数只算位置，动画只做 transform；离场格延迟摘除；说话者焦点去抖 800ms + 冷却 3s + 手动焦点保护 10s。

## 3. 前端组件与钩子

| 文件 | 职责 / 签名 |
| --- | --- |
| `components/live/StageGrid.tsx` | 按 `computeStageLayout` 渲染格子（绝对定位 + `transition: all 240ms`）；给举手格加 `is-hand`、焦点格加 `is-focus`、共享格加 `is-share` |
| `hooks/useFocusActions.ts` | `useFocusActions(roomId)` → `{ setFocus(userId), requestFocus(), approve(id), reject(id), exitFocus(), grantFromHand(userId), canGrant, myPending }` |
| `components/live/FocusBadge.tsx` | 举手格上的角标按钮：`给焦点` / `放下手`（仅 `canGrant` 时渲染）；焦点者格上：`退出焦点`（自己时才渲染） |
| `components/live/MicOrb.tsx` | 麦克风悬浮键：`audioLevel` 驱动波纹环（`scale = 1 + level * --mic-pulse-max`），静音/未发布时归零；点击切换静音 |
| `hooks/useAudioLevels.ts` | `useAudioLevels()` → `Record<userId, number>`（0~1），来源 `useTracks` 的 `audioLevel`（LiveKit 内置），节流 100ms |
| `components/live/RoomActionBar.tsx`（改） | 举手按钮文案与行为按角色分流：房主 =「取得焦点」（`setFocus(self)`）、协管 =「申请焦点」（`requestFocus()`）、参与者 =「举手」；自己处于焦点时该位置换「**退出焦点**」 |

## 4. 失败与边界

| 情况 | 处理 |
| --- | --- |
| 焦点者离开房间 | 焦点自动清（现有行为）；其 pending 申请一并 cancel |
| 批准的瞬间申请人已离开 | 事务内校验成员仍在册，否则 409 并置 `cancelled` |
| 两人同时点是 | `ux_focus_requests_pending` + `FOR UPDATE`：第二个拿到已存在行（幂等） |
| 房间已结束 | 全部焦点/举手/申请接口 409 `ROOM_ENDED` |
| 只剩 1 人 | 布局铺满（mode='uniform'，1 格占满区域） |
| `audioLevel` 缺失（浏览器不支持） | 声波恒零，按钮仍可用（降级不报错） |

## 5. 文档产出（硬产出）

- 本文 + 需求单 + ADR-0021；实现页 `docs/02-modules/r009-focus-system.md` + 功能页 `…-features.md`；台账 `changes.md` + `review.md`；索引/roadmap 回填。
