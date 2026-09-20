/** r012 在线心跳（Q14=2：前端短轮询，不是「请求即心跳」）。
 *
 * 三条约束：
 *   ① 周期单点可调：`PRESENCE_BEAT_MS`（默认 60 秒）；
 *   ② 只在「已登录 + 页面可见」时真发 —— 不可见时跳过，不空跑请求（沿用 useRosterSync 的判据）；
 *   ③ 失败静默：下一次周期再试，不打扰用户（在线口径允许一次丢包，见后端判据窗口）。
 */
import { useEffect } from 'react'

import { presenceApi } from '../api/presence'
import { useSession } from './useSession'

/** 心跳周期（毫秒）——单点可调；与后端 PRESENCE_ONLINE_SECONDS（默认 120 秒）成 2:1。 */
export const PRESENCE_BEAT_MS = 60_000

export function usePresenceBeat(): void {
  const { user } = useSession()

  useEffect(() => {
    if (!user) return
    let cancelled = false

    const beat = () => {
      if (cancelled || document.visibilityState !== 'visible') return
      void presenceApi.beat().catch(() => {
        /* 心跳失败静默：下一周期重试，不影响界面 */
      })
    }

    beat() // 登录/首屏立刻补一次，避免最长一整个周期内显示离线
    const timer = window.setInterval(beat, PRESENCE_BEAT_MS)
    document.addEventListener('visibilitychange', beat)
    return () => {
      cancelled = true
      window.clearInterval(timer)
      document.removeEventListener('visibilitychange', beat)
    }
  }, [user])
}

export default usePresenceBeat
