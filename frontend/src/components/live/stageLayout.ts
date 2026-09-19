/** 舞台布局的**唯一**派生函数：焦点是谁、缩格怎么排、框多大（纯函数，可单测/肉眼验）。
 *
 * 设计事实源：docs/rounds/r004-room-extras/design.md §7.1~§7.7（焦点优先级、尺寸阶梯、变换清单）
 * 口径（§7.3 四条防意外原则）：
 *   ① 缩格尺寸恒定（176×99），人数只改「数量与列数」；
 *   ② 焦点格只在 k=4 与 k=7 两个门槛变尺寸；
 *   ③ 焦点易手是唯一「大↔小」事件，由本函数一次性算出，组件只渲染；
 *   ④ 共享不改变任何尺寸，只换焦点格的内容。
 * 常量与 global.css 的 `--live-rail-*` / `--focus-min-*` 一一对应（改一处要同步另一处，见风格指南 §12.1）。
 */
export const RAIL_WIDTH = 176
export const RAIL_GAP = 12
export const RAIL_MAX_ROWS = 3
export const RAIL_TILE = { w: 176, h: 99 } as const
export const FOCUS_MIN_WIDTH = 480
export const FOCUS_MIN_WIDTH_SQUEEZE = 320
export const FOCUS_RATIO = 16 / 9
/** 可用高度的推导与 r002 一致：视口高扣掉状态条/控制坞/提示的让位。 */
export const FOCUS_MAX_HEIGHT = () => Math.max(180, window.innerHeight - 250)

export type RailMode = 'none' | 'single' | 'double' | 'triple' | 'strip'
export type FocusKind = 'share' | 'focus' | 'speaker' | 'self'

export interface StageLayout {
  focus: { identity: string; kind: FocusKind } | null
  rail: { identity: string; speaking: boolean }[]
  railMode: RailMode
  metrics: { railWidth: number; railColumns: number; railTile: typeof RAIL_TILE; focusMaxWidth: number; focusMaxHeight: number }
}

export interface StageLayoutInput {
  /** 在线 identity（含自己）——只放在场的人，离线/非成员不进舞台（§7.5）。 */
  online: string[]
  selfIdentity: string
  /** 服务端同步的手动焦点（ADR-0014）；为空表示没有。 */
  focusUserId: string | null
  /** 焦点对象是否仍是**在册**成员：否 → 焦点失效回落（§8.7 边界态）。 */
  focusActive: boolean
  /** 正在共享屏幕的人（无则 null）。 */
  shareIdentity: string | null
  speakerIdentity: string | null
  viewport: { w: number; h: number }
  /** 屏幕共享轨的参与者 identity（共享者即使不在 online 列表也要当焦点）。 */
}

function pickFocus(input: StageLayoutInput): { identity: string; kind: FocusKind } | null {
  const { shareIdentity, focusUserId, focusActive, speakerIdentity, selfIdentity, online } = input
  if (shareIdentity) return { identity: shareIdentity, kind: 'share' }
  if (focusUserId && focusActive) return { identity: focusUserId, kind: 'focus' }
  const speaker = speakerIdentity && online.includes(speakerIdentity) ? speakerIdentity : null
  if (speaker && speaker !== selfIdentity) return { identity: speaker, kind: 'speaker' }
  if (selfIdentity) return { identity: selfIdentity, kind: 'self' }
  const first = online[0]
  return first ? { identity: first, kind: 'self' } : null
}

export function computeStageLayout(input: StageLayoutInput): StageLayout {
  const focus = pickFocus(input)
  const railIdentities = input.online.filter((identity) => identity !== focus?.identity)
  const k = railIdentities.length
  const portrait = input.viewport.w < input.viewport.h

  const focusMaxHeight = Math.max(180, input.viewport.h - 250)
  const byRatio = focusMaxHeight * FOCUS_RATIO
  const usable = Math.max(200, input.viewport.w - 48) // 与 .live-shell 左右内边距一致

  let railMode: RailMode = 'none'
  let railColumns = 0
  if (k > 0) {
    if (portrait) {
      railMode = 'strip'
      railColumns = Math.max(1, Math.floor((usable + RAIL_GAP) / (RAIL_WIDTH + RAIL_GAP)))
    } else if (k <= RAIL_MAX_ROWS) {
      railMode = 'single'
      railColumns = 1
    } else if (k <= RAIL_MAX_ROWS * 2) {
      railMode = 'double'
      railColumns = 2
    } else {
      railColumns = 3
      const remaining = usable - railColumns * RAIL_WIDTH - (railColumns - 1) * RAIL_GAP - RAIL_GAP
      railMode = remaining >= FOCUS_MIN_WIDTH ? 'triple' : 'strip'
      if (railMode === 'strip') railColumns = Math.max(1, Math.floor((usable + RAIL_GAP) / (RAIL_WIDTH + RAIL_GAP)))
    }
  }

  const railWidth = railMode === 'strip' || railMode === 'none' ? 0 : railColumns * RAIL_WIDTH + (railColumns - 1) * RAIL_GAP
  const focusMaxWidth = Math.max(
    FOCUS_MIN_WIDTH_SQUEEZE,
    Math.min(usable - (railMode === 'strip' ? 0 : railWidth + RAIL_GAP), byRatio),
  )

  return {
    focus,
    rail: railIdentities.map((identity) => ({ identity, speaking: identity === input.speakerIdentity })),
    railMode,
    metrics: { railWidth, railColumns, railTile: RAIL_TILE, focusMaxWidth, focusMaxHeight },
  }
}
