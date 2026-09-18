/** 专注态：静默 N 秒后界面退场（参数单点可调，见 docs/04-style/global-style.md §12.1）。
 *
 * 指针移动 / 键盘聚焦 / 滚轮 / 有人说话都会重置计时；`prefers-reduced-motion` 只影响动效，不影响本逻辑。
 */
import { useEffect, useRef, useState } from 'react'

export function useChromeIdle(seconds: number, active = false): boolean {
  const [idle, setIdle] = useState(false)
  const timer = useRef<number | null>(null)

  useEffect(() => {
    if (active) {
      setIdle(false)
      return
    }
    const reset = () => {
      setIdle(false)
      if (timer.current !== null) window.clearTimeout(timer.current)
      timer.current = window.setTimeout(() => setIdle(true), seconds * 1000)
    }
    reset()
    window.addEventListener('pointermove', reset)
    window.addEventListener('pointerdown', reset)
    window.addEventListener('keydown', reset)
    window.addEventListener('wheel', reset)
    return () => {
      if (timer.current !== null) window.clearTimeout(timer.current)
      window.removeEventListener('pointermove', reset)
      window.removeEventListener('pointerdown', reset)
      window.removeEventListener('keydown', reset)
      window.removeEventListener('wheel', reset)
    }
  }, [seconds, active])

  return idle
}
