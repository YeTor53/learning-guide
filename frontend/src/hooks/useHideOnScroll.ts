/** 滚动时自动隐藏顶栏（r007 追加需求：**任何一点往下划就隐藏** {@link useHideOnScroll}）。
 *
 * 口径（用户 2026-09-19）：向下滚动 → 顶栏滑走；向上滚动或回到顶部 → 顶栏回来。
 * - `threshold`：判定「真的滚了」的最小位移（默认 4px，避免抖动误触）。
 * - 用 rAF 合并滚动事件，滚动处理器只读 `scrollY`，不写样式（写样式交给 CSS 过渡）。
 * - 顶栏是 `position: sticky`，所以隐藏 = `transform: translateY(-100%)`（CSS 里维护）。
 */
import { useEffect, useState } from 'react'

export default function useHideOnScroll(threshold = 4): boolean {
  const [hidden, setHidden] = useState(false)

  useEffect(() => {
    let last = window.scrollY
    let queued = false

    const apply = () => {
      queued = false
      const y = window.scrollY
      if (Math.abs(y - last) < threshold) return
      // 向下且已离开顶部 → 隐藏；向上或回到顶部 → 显示
      setHidden(y > last && y > 0)
      last = y
    }

    const onScroll = () => {
      if (queued) return
      queued = true
      requestAnimationFrame(apply)
    }

    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
    }
  }, [threshold])

  return hidden
}
