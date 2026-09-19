/** 唯一动画实现（r009）：布局变化一律走 FLIP，参数从 CSS 令牌读（改 :root 一处即生效）。
 *
 * 设计事实源：docs/rounds/r009-focus-system/motion-design.md（§2 三条硬规则、§3 令牌表、§5 实测口径）。
 * 硬规则：① 几何只用 transform（不做 width/height 动画）② 时长恒定为令牌值 ③ 变化期间不阻塞交互。
 */
import { useEffect, useLayoutEffect, useRef, useState } from 'react'

/** 读 `:root` 上的 CSS 令牌；取不到就用兜底值（保证组件在测试/无样式环境也不炸）。 */
export function readToken(name: string, fallback: number): number {
  if (typeof window === 'undefined') return fallback
  const raw = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  const value = Number.parseFloat(raw)
  return Number.isFinite(value) ? value : fallback
}

export function readEase(fallback = 'cubic-bezier(.22,1,.36,1)'): string {
  if (typeof window === 'undefined') return fallback
  return getComputedStyle(document.documentElement).getPropertyValue('--stage-ease').trim() || fallback
}

export function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || !window.matchMedia) return false
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

export interface FlipOptions {
  /** 变化指纹：人数 + 焦点 + 共享 + 尺寸。变化即触发一次 FLIP。 */
  layoutKey: string
  moveMs?: number
  enterMs?: number
  /** 只记录、不播放（用于测试或初始化）。 */
  disabled?: boolean
}

/**
 * FLIP：读旧矩形 → 应用新布局 → 反向 transform → 播放到原位。
 *
 * - 节点用 `data-flip-id=<identity>` 标注（保持 `key` 稳定，同一个人的 `<video>` 不重建，避免黑帧）；
 * - 新出现的节点播进入动画（fade + scale .92→1）；
 * - 动画中再次变化时先 `cancel()` 上一段，从当前可见位置继续（不回弹）；
 * - `prefers-reduced-motion` 时时长归零（瞬间到位，几何仍正确）。
 */
export function useFlipTransition(container: HTMLElement | null, options: FlipOptions): void {
  const { layoutKey, disabled } = options
  const prev = useRef(new Map<string, DOMRect>())

  useLayoutEffect(() => {
    if (!container) return
    const reduced = prefersReducedMotion()
    const moveMs = reduced ? 0 : options.moveMs ?? readToken('--stage-move-ms', 240)
    const enterMs = reduced ? 0 : options.enterMs ?? readToken('--stage-enter-ms', 220)
    const ease = readEase()
    const nodes = Array.from(container.querySelectorAll<HTMLElement>('[data-flip-id]'))
    const next = new Map<string, DOMRect>()

    for (const node of nodes) {
      const id = node.dataset.flipId
      if (!id) continue
      const rect = node.getBoundingClientRect()
      next.set(id, rect)
      const before = prev.current.get(id)
      // 上段动画未播完就再次变化：先取消，从当前可见位置继续
      node.getAnimations().forEach((animation) => animation.cancel())
      if (disabled) continue
      if (!before) {
        if (enterMs > 0) {
          node.animate(
            [
              { opacity: 0, transform: 'scale(.92)' },
              { opacity: 1, transform: 'none' },
            ],
            { duration: enterMs, easing: ease },
          )
        }
        continue
      }
      const dx = before.left - rect.left
      const dy = before.top - rect.top
      const sx = rect.width > 0 ? before.width / rect.width : 1
      const sy = rect.height > 0 ? before.height / rect.height : 1
      const moved = Math.abs(dx) > 0.5 || Math.abs(dy) > 0.5
      const resized = Math.abs(sx - 1) > 0.01 || Math.abs(sy - 1) > 0.01
      if (!moved && !resized) continue
      node.animate(
        [
          { transform: `translate(${dx}px, ${dy}px) scale(${sx}, ${sy})` },
          { transform: 'none' },
        ],
        { duration: moveMs, easing: ease },
      )
    }
    prev.current = next
  }, [container, layoutKey, disabled, options.moveMs, options.enterMs])
}

/**
 * 离场格延迟摘除（motion-design C2）：先让邻居开始补位，离场格淡出后才从 DOM 移除。
 *
 * 返回「要渲染的 id 列表」= 当前集合 ∪ 正在淡出的旧集合；`prefers-reduced-motion` 时立即移除。
 */
export function useLeavingIds(currentIds: string[], exitMs?: number): string[] {
  const exit = exitMs ?? readToken('--stage-exit-ms', 180)
  const key = currentIds.join('|')
  const [leaving, setLeaving] = useState<string[]>([])
  const previous = useRef<string[]>([])

  useEffect(() => {
    const gone = previous.current.filter((id) => !currentIds.includes(id))
    previous.current = currentIds
    if (gone.length === 0) return
    if (prefersReducedMotion()) return
    setLeaving(gone)
    const timer = window.setTimeout(() => setLeaving([]), Math.max(0, exit))
    return () => window.clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, exit])

  return leaving.length === 0 ? currentIds : [...currentIds, ...leaving]
}
