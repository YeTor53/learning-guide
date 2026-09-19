/** 举手状态：HTTP 落库 + 房内全量快照广播（快照按 `at` 收敛，后到覆盖先到）。
 *
 * 设计事实源：docs/rounds/r004-room-extras/design.md §5.5、§6
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { Room } from 'livekit-client'

import { roomExtrasApi } from '../api/roomExtras'
import type { Hand } from '../api/roomExtras'
import { CHANNEL_TOPIC, publishSnapshot, useDataChannel } from './useDataChannel'

export interface HandState {
  hands: Hand[]
  mine: boolean
  error: string | null
  refresh: () => Promise<void>
  raise: () => Promise<void>
  lower: () => Promise<void>
  lowerOther: (userId: string) => Promise<void>
}

interface HandsSnapshot {
  v: number
  at: number
  hands: Hand[]
}

export function useHandRaise(room: Room | null, roomId: string | null, enabled: boolean, myUserId: string | null): HandState {
  const [hands, setHands] = useState<Hand[]>([])
  const [error, setError] = useState<string | null>(null)
  const atRef = useRef(0)
  const roomIdRef = useRef(roomId)
  roomIdRef.current = roomId

  const applySnapshot = useCallback((next: Hand[], at: number) => {
    if (at < atRef.current) return
    atRef.current = at
    setHands(next)
  }, [])

  const refresh = useCallback(async () => {
    const id = roomIdRef.current
    if (!id) return
    try {
      const { hands: items } = await roomExtrasApi.listHands(id)
      atRef.current = 0
      setHands(items)
    } catch (err) {
      setError(err instanceof Error ? err.message : '举手状态加载失败')
    }
  }, [])

  useEffect(() => {
    if (enabled) void refresh()
  }, [enabled, refresh])

  useDataChannel<HandsSnapshot>(room, CHANNEL_TOPIC.hands, (snapshot) => {
    applySnapshot(snapshot.hands ?? [], snapshot.at ?? 0)
  })

  /** 所有写操作：HTTP 成功 → 用服务端快照覆盖本地 → 广播同一份快照。 */
  const run = useCallback(
    async (action: () => Promise<{ hands: Hand[] }>) => {
      try {
        const { hands: next } = await action()
        applySnapshot(next, Date.now())
        if (room) await publishSnapshot(room, CHANNEL_TOPIC.hands, { v: 1, at: Date.now(), hands: next })
      } catch (err) {
        setError(err instanceof Error ? err.message : '举手操作失败')
      }
    },
    [applySnapshot, room],
  )

  const raise = useCallback(async () => {
    const id = roomIdRef.current
    if (id) await run(() => roomExtrasApi.raiseHand(id))
  }, [run])

  const lower = useCallback(async () => {
    const id = roomIdRef.current
    if (id) await run(() => roomExtrasApi.lowerOwnHand(id))
  }, [run])

  const lowerOther = useCallback(
    async (userId: string) => {
      const id = roomIdRef.current
      if (id) await run(() => roomExtrasApi.lowerOtherHand(id, userId))
    },
    [run],
  )

  const mine = !!myUserId && hands.some((item) => item.userId === myUserId)
  return { hands, mine, error, refresh, raise, lower, lowerOther }
}
