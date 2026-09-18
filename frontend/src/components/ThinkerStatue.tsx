import { useEffect, useRef } from 'react'

interface Props {
  className?: string
}

/** 下移速率：滚动量的 10%（用户向下滚 100px，图版向下 10px） */
const FACTOR = 0.1
/** 虚拟下界 = 图版高度的 RATIO（与页面布局无关，保证任何页面尺寸下都有可用行程） */
const RATIO = 0.35
const MIN_LIMIT = 90
const MAX_LIMIT = 200

/**
 * 首屏右侧的《思想者》图版（罗丹，已镜像）。
 *
 * 位移规则：
 * - **虚拟上界 0**：页面在顶部时图版在最高位；
 * - 向下滚动时按滚动量的 **10%** 向下移动；
 * - **虚拟下界 = 图版高度 × 35%（90–200px）**：与页面布局无关，不随页面长短/大小失效；
 * - **允许被下方遮挡**：图版外层有一个裁剪容器，下边正好落在房间列表区顶线，
 *   所以越过该线的部分会被「吃掉」（视觉上像滑到列表区下面），不会压住列表内容；
 * - `prefers-reduced-motion: reduce` 时不绑定滚动，静止在最高位。
 *
 * 实现：滚动用 rAF 合帧 + passive 监听；虚拟下界按图版自身高度测算（高度不随位移变化，
 * 因此无需清空 transform 即可测量）。资材与许可见 `docs/03-decisions/r001-adr-0010-visual-assets.md`。
 */
export default function ThinkerStatue({ className }: Props) {
  const ref = useRef<HTMLImageElement | null>(null)

  useEffect(() => {
    const node = ref.current
    if (!node) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

    let frame = 0
    let limit = MIN_LIMIT

    const measure = () => {
      const height = node.getBoundingClientRect().height
      limit = Math.min(MAX_LIMIT, Math.max(MIN_LIMIT, Math.round(height * RATIO)))
    }

    const apply = () => {
      frame = 0
      const offset = Math.max(0, Math.min(window.scrollY * FACTOR, limit))
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
    <div className={`hero-thinker-clip ${className ?? ''}`.trim()} aria-hidden>
      <img
        ref={ref}
        className="hero-thinker"
        src="/thinker.webp"
        alt=""
        draggable={false}
        decoding="async"
        title="《思想者》· 奥古斯特·罗丹（罗丹博物馆藏）"
      />
    </div>
  )
}
