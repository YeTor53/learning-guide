/** 舞台几何（r009）：**均分铺满** + 焦点跨 2 格 + 共享占主区。
 *
 * 设计事实源：docs/rounds/r009-focus-system/design.md §1、motion-design.md（动效只做 transform，几何必须纯函数）。
 * 与旧 `stageLayout.ts` 的关系：旧实现（焦点主格 + 右侧缩格阶梯）在 r009 cp-1b 被本模块取代；
 * 旧文件已于 r009.5（2026-09-20）删除（零引用死代码），历史版本见 git（删除前最后版本 `e3571be`）。
 *
 * 纯函数、无副作用：给定区域尺寸与在场者，返回每格的像素矩形；不读 DOM、不读时间。
 */

export type StageMode = 'empty' | 'uniform' | 'focus' | 'share'
export type TileKind = 'grid' | 'focus' | 'share'

export interface Rect {
  x: number
  y: number
  w: number
  h: number
}

export interface StageTile extends Rect {
  identity: string
  kind: TileKind
}

export interface StageGeometryInput {
  /** 区域可用尺寸（已扣掉内边距）。 */
  areaW: number
  areaH: number
  /** 参与排布的人（顺序即稳定排序后的顺序：本地 → 焦点 → 举手 → 加入时间）。 */
  identities: string[]
  /** 手动焦点（可空）。 */
  focusIdentity?: string | null
  /** 正在共享屏幕的人（可空）——共享优先于焦点（ADR-0014 优先级保留）。 */
  shareIdentity?: string | null
  /** 格子间距，默认取 `--stage-gap`。 */
  gap?: number
  /** 目标宽高比（默认 16/9）。 */
  aspect?: number
}

export interface StageGeometry {
  mode: StageMode
  tiles: StageTile[]
  /** 焦点身份（= 共享者或手动焦点；用于徽标与无障碍标注）。 */
  focusIdentity: string | null
}

export const DEFAULT_GAP = 10
export const TARGET_ASPECT = 16 / 9
/** 共享时人像条的高度占比（剩下给共享主区）。 */
export const SHARE_STRIP_RATIO = 0.22
/** 焦点格份量：所在行列各放大 1.4 倍（≈ 面积 1.96 倍；用户口径「得到焦点时框放大」，1.4 倍边长）。 */
export const FOCUS_WEIGHT = 1.4

/** 由槽位数选列数：最接近目标宽高比，且 `cols * rows >= slots` 且不留空行。 */
export function bestGrid(slots: number, areaW: number, areaH: number, aspect: number = TARGET_ASPECT): { cols: number; rows: number } {
  if (slots <= 1) return { cols: 1, rows: 1 }
  let best = { cols: 1, rows: slots, score: Number.POSITIVE_INFINITY }
  for (let cols = 1; cols <= slots; cols += 1) {
    const rows = Math.ceil(slots / cols)
    const cellW = areaW / cols
    const cellH = areaH / rows
    if (cellH <= 0 || cellW <= 0) continue
    const ratio = cellW / cellH
    // 目标：格子比例接近 aspect；同时尽量少留空槽（slots 与 cols*rows 的差）
    const empty = cols * rows - slots
    // 空槽用「重罚」：实测 3 人时轻罚会选 2×2（比例最好但空一格）→ 铺满率只剩 73%
    const score = Math.abs(Math.log(ratio / aspect)) + empty * 2.0
    if (score < best.score) best = { cols, rows, score }
  }
  return { cols: best.cols, rows: best.rows }
}

/** 把区域均分成 cols×rows 个矩形：整数像素 + 余数分给靠前的行列（不出现 1px 缝）。 */
export function distribute(areaW: number, areaH: number, cols: number, rows: number, gap: number): Rect[] {
  const totalGapX = gap * (cols - 1)
  const totalGapY = gap * (rows - 1)
  const usableW = Math.max(0, areaW - totalGapX)
  const usableH = Math.max(0, areaH - totalGapY)
  const baseW = Math.floor(usableW / cols)
  const baseH = Math.floor(usableH / rows)
  const extraW = usableW - baseW * cols
  const extraH = usableH - baseH * rows
  const colW: number[] = []
  const rowH: number[] = []
  for (let c = 0; c < cols; c += 1) colW.push(baseW + (c < extraW ? 1 : 0))
  for (let r = 0; r < rows; r += 1) rowH.push(baseH + (r < extraH ? 1 : 0))
  const rects: Rect[] = []
  let y = 0
  for (let r = 0; r < rows; r += 1) {
    let x = 0
    for (let c = 0; c < cols; c += 1) {
      rects.push({ x, y, w: colW[c], h: rowH[r] })
      x += colW[c] + gap
    }
    y += rowH[r] + gap
  }
  return rects
}

/**
 * 加权均分：在 `distribute` 基础上给指定行列乘以权重（焦点格「份量 1.4 倍」靠这个实现）。
 *
 * 关键：仍按整块区域切分（**不留空洞**），权重只改变各行列的尺寸分配；
 * 权重同一行/列的其它格子会相应变小——这是「焦点更大」的代价，也是视觉上最自然的表达。
 */
export function distributeWeighted(
  areaW: number,
  areaH: number,
  cols: number,
  rows: number,
  gap: number,
  wx: number[] = [],
  wy: number[] = [],
): Rect[] {
  const weightSum = (list: number[], count: number) => {
    if (list.length !== count) return count
    const total = list.reduce((a, b) => a + b, 0)
    return total > 0 ? total : count
  }
  const totalGapX = gap * (cols - 1)
  const totalGapY = gap * (rows - 1)
  const usableW = Math.max(0, areaW - totalGapX)
  const usableH = Math.max(0, areaH - totalGapY)
  const sumX = weightSum(wx, cols)
  const sumY = weightSum(wy, rows)
  const rawW = Array.from({ length: cols }, (_, c) => (wx.length === cols ? (usableW * wx[c]) / sumX : usableW / cols))
  const rawH = Array.from({ length: rows }, (_, r) => (wy.length === rows ? (usableH * wy[r]) / sumY : usableH / rows))
  // 取整并把余数补给靠前的行列（避免缝/溢出）
  const colW = rawW.map((value) => Math.floor(value))
  const rowH = rawH.map((value) => Math.floor(value))
  let leftW = usableW - colW.reduce((a, b) => a + b, 0)
  for (let c = 0; c < cols && leftW > 0; c += 1) {
    colW[c] += 1
    leftW -= 1
  }
  let leftH = usableH - rowH.reduce((a, b) => a + b, 0)
  for (let r = 0; r < rows && leftH > 0; r += 1) {
    rowH[r] += 1
    leftH -= 1
  }
  const rects: Rect[] = []
  let y = 0
  for (let r = 0; r < rows; r += 1) {
    let x = 0
    for (let c = 0; c < cols; c += 1) {
      rects.push({ x, y, w: colW[c], h: rowH[r] })
      x += colW[c] + gap
    }
    y += rowH[r] + gap
  }
  return rects
}


/** 合并网格里的两个相邻槽位（焦点格跨格用）：同列优先竖向，否则横向。 */
export function mergeSlots(rects: Rect[], a: number, b: number, gap: number): Rect {
  const first = rects[a]
  const second = rects[b]
  const x = Math.min(first.x, second.x)
  const y = Math.min(first.y, second.y)
  const right = Math.max(first.x + first.w, second.x + second.w)
  const bottom = Math.max(first.y + first.h, second.y + second.h)
  void gap
  return { x, y, w: right - x, h: bottom - y }
}

/**
 * 主入口：算「谁在哪、多大」。
 *
 * - 有共享：mode='share'，共享格占主区（顶部 16:9 或剩余高度），其余人像铺满底部一条（一行优先）；
 * - 有焦点：mode='focus'，槽位 = n + 1，焦点格占前两个相邻槽位（≈1.4 倍边长）；焦点不在场时退化为均分；
 * - 其余：mode='uniform'，n 格均分铺满；n=0 → mode='empty'。
 */
export function computeStageGeometry(input: StageGeometryInput): StageGeometry {
  const { areaW, areaH, identities } = input
  const gap = input.gap ?? DEFAULT_GAP
  const aspect = input.aspect ?? TARGET_ASPECT
  const focusIdentity = input.shareIdentity ?? input.focusIdentity ?? null
  if (areaW <= 0 || areaH <= 0 || identities.length === 0) {
    return { mode: 'empty', tiles: [], focusIdentity }
  }

  // —— 共享：主区 + 底部人像条
  if (input.shareIdentity && identities.includes(input.shareIdentity)) {
    const sharer = input.shareIdentity
    const others = identities.filter((id) => id !== sharer)
    const stripH = others.length === 0 ? 0 : Math.round((areaH - gap) * SHARE_STRIP_RATIO)
    const mainH = others.length === 0 ? areaH : areaH - gap - stripH
    const tiles: StageTile[] = [{ identity: sharer, kind: 'share', x: 0, y: 0, w: areaW, h: mainH }]
    if (others.length > 0) {
      const { cols, rows } = bestGrid(others.length, areaW, stripH, aspect)
      const rects = distribute(areaW, stripH, cols, rows, gap)
      others.forEach((identity, index) => {
        const rect = rects[index]
        if (rect) tiles.push({ identity, kind: 'grid', ...rect, y: rect.y + mainH + gap })
      })
    }
    return { mode: 'share', tiles, focusIdentity: sharer }
  }

  // —— 焦点：网格仍按 n 人算，但焦点所在行/列的权重放大到 FOCUS_WEIGHT（≈1.4 倍边长）
  const focused = input.focusIdentity && identities.includes(input.focusIdentity) ? input.focusIdentity : null
  const slots = identities.length
  const { cols, rows } = bestGrid(slots, areaW, areaH, aspect)
  if (!focused) {
    const rects = distribute(areaW, areaH, cols, rows, gap)
    return {
      mode: 'uniform',
      focusIdentity: null,
      tiles: identities.map((identity, index) => ({ identity, kind: 'grid', ...(rects[index] ?? { x: 0, y: 0, w: 0, h: 0 }) })),
    }
  }

  const others = identities.filter((id) => id !== focused)
  // 焦点格固定放第一个槽位（左上）→ 它的列=0、行=0；权重放大后其余格自然让位
  const wx = Array.from({ length: cols }, (_, c) => (c === 0 ? FOCUS_WEIGHT : 1))
  const wy = Array.from({ length: rows }, (_, r) => (r === 0 ? FOCUS_WEIGHT : 1))
  const rects = distributeWeighted(areaW, areaH, cols, rows, gap, wx, wy)
  const tiles: StageTile[] = [{ identity: focused, kind: 'focus', ...(rects[0] ?? { x: 0, y: 0, w: 0, h: 0 }) }]
  others.forEach((identity, index) => {
    const rect = rects[index + 1]
    if (rect) tiles.push({ identity, kind: 'grid', ...rect })
  })
  return { mode: 'focus', tiles, focusIdentity: focused }
}

/** 无障碍/调试用：把几何描述成一行（测试与日志共用）。 */
export function describeGeometry(geometry: StageGeometry): string {
  const parts = geometry.tiles.map((tile) => `${tile.identity}:${tile.kind}:${tile.w}x${tile.h}@${tile.x},${tile.y}`)
  return `${geometry.mode}|${parts.join(' ')}`
}
