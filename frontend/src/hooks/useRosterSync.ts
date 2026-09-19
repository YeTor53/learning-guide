/** 名册 / 待批变更同步（r006，ADR-0017 D2）。
 *
 * 三条路，缺一不可：
 *   ① 收到别端的 `lg.roster` 广播 → 立刻重取（秒级一致）；
 *   ② 关键时刻：进房 / 重连成功、窗口聚焦、页面重新可见 → 重取；
 *   ③ 兜底：30 秒轮询（仅页面可见时真取）—— 广播丢了也能自己拉平。
 *
 * 口径：HTTP 落库是唯一真相，广播只是加速层（ADR-0013 的沿用）。返回值 = 本端动作后要调的广播函数。
 */
import { useCallback, useEffect, useRef } from 'react'
import { Room } from 'livekit-client'

import { CHANNEL_TOPIC, publishSnapshot, useDataChannel } from './useDataChannel'

/** 兜底轮询周期（毫秒）：单点可调。 */
export const ROSTER_POLL_MS = 30_000

export interface RosterSignal {
  v: 1
  at: number
  actorIdentity: string
}

export function useRosterSync(
  room: Room | null,
  connected: boolean,
  onChanged: () => void,
): () => Promise<void> {
  const handlerRef = useRef(onChanged)
  handlerRef.current = onChanged

  // ① 别端的广播
  useDataChannel<RosterSignal>(room, CHANNEL_TOPIC.roster, () => handlerRef.current())

  const broadcast = useCallback(async () => {
    if (!room || !connected) return
    await publishSnapshot(room, CHANNEL_TOPIC.roster, {
      v: 1,
      at: Date.now(),
      actorIdentity: room.localParticipant.identity,
    } satisfies RosterSignal)
  }, [room, connected])

  // ② 进房 / 重连成功
  useEffect(() => {
    if (connected) handlerRef.current()
  }, [connected])

  // ② 窗口聚焦 / 页面重新可见
  useEffect(() => {
    const onFocus = () => handlerRef.current()
    const onVisible = () => {
      if (document.visibilityState === 'visible') handlerRef.current()
    }
    window.addEventListener('focus', onFocus)
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      window.removeEventListener('focus', onFocus)
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [])

  // ③ 兜底轮询（不可见时跳过，不空跑请求）
  useEffect(() => {
    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') handlerRef.current()
    }, ROSTER_POLL_MS)
    return () => window.clearInterval(timer)
  }, [])

  return broadcast
}
