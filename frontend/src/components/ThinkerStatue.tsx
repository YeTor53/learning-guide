import { useEffect, useRef } from 'react'

/**
 * 位移幅度：可调参数（单点可调）
 * - 值 = 图版向下位移占滚动量的比例；默认 0.35，约一个首屏高度的滚动量即可走完全程；
 * - 建议区间 0.10 ~ 0.60（0.1 = 很含蓄，0.5 = 很快走到底）；
 * - 位移永远被容器夹住：offset = clamp(scrollY × AMPLITUDE, 0, 容器高 − 图版高)。
 */
const AMPLITUDE = 0.35

/** 系统开启「减少动效」时幅度打这个折扣（不彻底关掉，保证仍能看到位移） */
const REDUCED_MOTION_SCALE = 0.5

/**
 * 首屏右侧的《思想者》图版：**在一个固定容器内滑动**。
 *
 * 容器（`.thinker-box`，几何全在 CSS 参数区里，改那几个数即可）：
 * - 宽 = 图版宽（等宽）；
 * - 高 = 图版高 × 1.4 → 多出来的 0.4 倍就是图版的可滑动行程；
 * - 顶部略高于页面顶；底部略低于房间块的底边；`overflow: clip` 保证图版不越出容器。
 *
 * 行为：
 * - 页面在顶部 → 图版在容器内的最高位；
 * - 向下滚动 → 图版按 `AMPLITUDE` 的比例向下走（幅度很小、可调），到达容器底部即停；
 * - 位移只在容器内部发生，图版既不会跑出首屏，也不会压住下方内容之外的区域。
 *
 * 资材来源与许可见 `docs/03-decisions/r001-adr-0010-visual-assets.md`。
 */
export default function ThinkerStatue() {
  const imgRef = useRef<HTMLImageElement | null>(null)

  useEffect(() => {
    const node = imgRef.current
    const box = node?.parentElement
    if (!node || !box) return

    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const amplitude = AMPLITUDE * (reduced ? REDUCED_MOTION_SCALE : 1)

    let frame = 0
    /** 可滑动行程 = 容器高 − 图版高（由 CSS 参数区决定） */
    let travel = 0

    const measure = () => {
      travel = Math.max(0, box.clientHeight - node.clientHeight)
    }

    const apply = () => {
      frame = 0
      const offset = Math.max(0, Math.min(window.scrollY * amplitude, travel))
      node.style.transform = `translate3d(0, ${offset.toFixed(2)}px, 0)`
    }

    const onScroll = () => {
      if (!frame) frame = window.requestAnimationFrame(apply)
    }
    const onResize = () => {
      measure()
      apply()
    }

    measure()
    apply()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onResize)
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onResize)
      if (frame) window.cancelAnimationFrame(frame)
    }
  }, [])

  return (
    <div className="thinker-box">
      <img
        ref={imgRef}
        className="thinker-img"
        src="/thinker.webp"
        alt=""
        aria-hidden
        draggable={false}
        decoding="async"
        title="《思想者》· 奥古斯特·罗丹（罗丹博物馆藏）"
      />
    </div>
  )
}
