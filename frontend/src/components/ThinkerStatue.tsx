import { useEffect, useRef } from 'react'

interface Props {
  className?: string
}

/** 视差强度与上下限（px）：位移 = clamp(-scrollY * FACTOR, ±LIMIT) */
const FACTOR = 0.14
const LIMIT = 48

/**
 * 首屏右侧的《思想者》图版（罗丹）——随页面滚动产生轻微位移。
 *
 * - 位移只在 ±48px 内（克制，整个首屏可见期间连续变化，不会早早触顶），用 rAF 合帧，滚动监听 passive；
 * - `prefers-reduced-motion: reduce` 时不绑定滚动，图片静止；
 * - 纯装饰：`alt=""` + `aria-hidden`，不参与语义与键盘；
 * - 资材来源、许可与处理过程见 `docs/03-decisions/r001-adr-0010-visual-assets.md`。
 */
export default function ThinkerStatue({ className }: Props) {
  const ref = useRef<HTMLImageElement | null>(null)

  useEffect(() => {
    const node = ref.current
    if (!node) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

    let frame = 0
    const apply = () => {
      frame = 0
      const raw = -window.scrollY * FACTOR
      const offset = Math.max(-LIMIT, Math.min(LIMIT, raw))
      node.style.transform = `translate3d(0, ${offset.toFixed(2)}px, 0)`
    }
    const onScroll = () => {
      if (!frame) frame = window.requestAnimationFrame(apply)
    }

    apply()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => {
      window.removeEventListener('scroll', onScroll)
      if (frame) window.cancelAnimationFrame(frame)
    }
  }, [])

  return (
    <img
      ref={ref}
      className={className}
      src="/thinker.webp"
      alt=""
      aria-hidden
      draggable={false}
      decoding="async"
      title="《思想者》· 奥古斯特·罗丹（罗丹博物馆藏）"
    />
  )
}
