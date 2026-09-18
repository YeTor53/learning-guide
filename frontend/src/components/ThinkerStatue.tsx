import { useEffect, useRef } from 'react'

interface Props {
  className?: string
}

/** 下移速率：滚动量的 10%（用户向下滚 100px，图版向下 10px） */
const FACTOR = 0.1

/**
 * 首屏右侧的《思想者》图版（罗丹，已镜像）。
 *
 * 位移规则（用户指定）：
 * - 页面在顶部时，图版在**最高位**（位移 0）；
 * - 向下滚动时，图版按滚动量的 **10%** 向下移动（相对内容呈「变慢」的视差）；
 * - **下界**：图版底边不得越过房间列表区顶部（即 `.hero` 底边），到界即停；
 * - `prefers-reduced-motion: reduce` 时不绑定滚动，静止在最高位。
 *
 * 实现：滚动用 rAF 合帧 + passive 监听；可移动行程在挂载与窗口尺寸变化时实测一次
 * （临时清空 transform 量取未位移的几何，再还原），避免每帧触发布局抖动。
 * 资材来源、许可与处理见 `docs/03-decisions/r001-adr-0010-visual-assets.md`。
 */
export default function ThinkerStatue({ className }: Props) {
  const ref = useRef<HTMLImageElement | null>(null)

  useEffect(() => {
    const node = ref.current
    if (!node) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

    const hero = node.parentElement
    if (!hero) return

    let frame = 0
    let maxTravel = 0

    const measure = () => {
      const previous = node.style.transform
      node.style.transform = 'none'
      const statue = node.getBoundingClientRect()
      const boundary = hero.getBoundingClientRect()
      node.style.transform = previous
      maxTravel = Math.max(0, boundary.bottom - statue.bottom)
    }

    const apply = () => {
      frame = 0
      const offset = Math.min(window.scrollY * FACTOR, maxTravel)
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
