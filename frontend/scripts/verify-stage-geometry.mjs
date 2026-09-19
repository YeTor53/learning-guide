#!/usr/bin/env node
/** r009 几何校验（无需测试框架）：esbuild 转译 TS → 直接跑断言并打印实测数字。
 *
 * 用法：node frontend/scripts/verify-stage-geometry.mjs
 * 设计事实源：docs/rounds/r009-focus-system/motion-design.md §5（终点一致性 / 铺满率）
 */
import { build } from 'esbuild'
import { pathToFileURL } from 'node:url'
import { mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const entry = new URL('../src/components/live/stageGeometry.ts', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1')
const outdir = mkdtempSync(join(tmpdir(), 'stage-geo-'))
const outfile = join(outdir, 'stageGeometry.mjs')
await build({ entryPoints: [entry], outfile, format: 'esm', bundle: true, logLevel: 'error' })
const mod = await import(pathToFileURL(outfile).href)

const AREA = { w: 1160, h: 660 } // 1440×900 房间交流页里舞台的实际可用区域（r004 实测口径）
let failures = 0
const check = (name, ok, detail) => {
  console.log(`${ok ? '[OK ]' : '[FAIL]'} ${name} — ${detail}`)
  if (!ok) failures += 1
}

/** 铺满率 = 格子总面积 / 区域面积；面积差 = (max-min)/max。 */
function stats(tiles, area) {
  const areas = tiles.map((t) => t.w * t.h)
  const sum = areas.reduce((a, b) => a + b, 0)
  const max = Math.max(...areas)
  const min = Math.min(...areas)
  return { fill: sum / (area.w * area.h), spread: (max - min) / max, max, min }
}

for (const n of [1, 2, 3, 4, 6, 8]) {
  const ids = Array.from({ length: n }, (_, i) => `u${i + 1}`)
  const geo = mod.computeStageGeometry({ areaW: AREA.w, areaH: AREA.h, identities: ids })
  const s = stats(geo.tiles, AREA)
  const right = Math.max(...geo.tiles.map((t) => t.x + t.w))
  const bottom = Math.max(...geo.tiles.map((t) => t.y + t.h))
  check(
    `均分 ${n} 人`,
    geo.tiles.length === n && s.spread <= 0.05 && s.fill >= 0.9 && right <= AREA.w && bottom <= AREA.h,
    `mode=${geo.mode} 格=${geo.tiles.length} 面积差=${(s.spread * 100).toFixed(1)}% 铺满率=${(s.fill * 100).toFixed(1)}% 右缘=${right}/${AREA.w} 下缘=${bottom}/${AREA.h}`,
  )
}

for (const n of [3, 4, 6, 8]) {
  const ids = Array.from({ length: n }, (_, i) => `u${i + 1}`)
  const geo = mod.computeStageGeometry({ areaW: AREA.w, areaH: AREA.h, identities: ids, focusIdentity: 'u2' })
  const focus = geo.tiles.find((t) => t.kind === 'focus')
  const grid = geo.tiles.filter((t) => t.kind === 'grid')
  const base = grid.length ? grid.map((t) => t.w * t.h).reduce((a, b) => a + b, 0) / grid.length : 0
  const baseTile = grid[0]
  const weightW = focus && baseTile ? focus.w / baseTile.w : 0
  const weightH = focus && baseTile ? focus.h / baseTile.h : 0
  const weightArea = focus && baseTile ? (focus.w * focus.h) / (baseTile.w * baseTile.h) : 0
  const right = Math.max(...geo.tiles.map((t) => t.x + t.w))
  const overlap = geo.tiles.some((t, i) =>
    geo.tiles.some((o, j) => j > i && t.x < o.x + o.w && o.x < t.x + t.w && t.y < o.y + o.h && o.y < t.y + t.h),
  )
  check(
    `焦点 ${n} 人`,
    Boolean(focus) && weightArea >= 1.35 && Math.max(weightW, weightH) >= 1.35 && !overlap && right <= AREA.w && geo.tiles.length === n,
    `份量：面积=${weightArea.toFixed(2)}× 宽=${weightW.toFixed(2)}× 高=${weightH.toFixed(2)}×（单列/单行时只有一维放大） 基格面积=${base.toFixed(0)} 重叠=${overlap} 右缘=${right}/${AREA.w}`,
  )
}

for (const n of [3, 6]) {
  const ids = Array.from({ length: n }, (_, i) => `u${i + 1}`)
  const geo = mod.computeStageGeometry({ areaW: AREA.w, areaH: AREA.h, identities: ids, shareIdentity: 'u1', focusIdentity: 'u2' })
  const share = geo.tiles.find((t) => t.kind === 'share')
  check(
    `共享 ${n} 人（共享优先于焦点）`,
    geo.mode === 'share' && Boolean(share) && share.h > AREA.h * 0.6 && geo.tiles.length === n,
    `mode=${geo.mode} 共享=${share ? `${share.w}x${share.h}` : '无'} 格=${geo.tiles.length}`,
  )
}

console.log(failures === 0 ? '\nPASS 全部几何断言通过' : `\nFAIL ${failures} 项`)
process.exit(failures === 0 ? 0 : 1)
