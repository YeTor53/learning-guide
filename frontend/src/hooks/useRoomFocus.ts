/** 焦点发言：服务端同步的唯一焦点（房主/协管指定或取消）。
 *
 * 设计事实源：docs/rounds/r004-room-extras/design.md §5.5、§7.1（优先级派生在 LiveStage）
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { Room } from 'livekit-client'

import { roomExtrasApi } from '../api/roomExtras'
import type { Focus } from '../api/roomExtras'
import { CHANNEL_TOPIC, publishSnapshot, useDataChannel } from './useDataChannel'

const EMPTY_FOCUS: Focus = { subjectUserId: null, subjectName: null, actorUserId: null, setAt: null }

export interface FocusState {
  focus: Focus
  error: string | null
  refresh: () => Promise<void>
  setFocus: (userId: string | null) => Promise<void>
}

interface FocusSnapshot {
  v: number
  at: number
  focus: Focus
}

export function useRoomFocus(room: Room | null, roomId: string | null, enabled: boolean): FocusState {
  const [focus, setFocusState] = useState<Focus>(EMPTY_FOCUS)
  const [error, setError] = useState<string | null>(null)
  const atRef = useRef(0)
  const roomIdRef = useRef(roomId)
  roomIdRef.current = roomId

  const refresh = useCallback(async () => {
    const id = roomIdRef.current
    if (!id) return
    try {
      const { focus: next } = await roomExtrasApi.getFocus(id)
      atRef.current = 0
      setFocusState(next ?? EMPTY_FOCUS)
    } catch (err) {
      setError(err instanceof Error ? err.message : '焦点状态加载失败')
    }
  }, [])

  useEffect(() => {
    if (enabled) void refresh()
  }, [enabled, refresh])

  useDataChannel<FocusSnapshot>(room, CHANNEL_TOPIC.focus, (snapshot) => {
    const at = snapshot.at ?? 0
    if (at < atRef.current) return
    atRef.current = at
    setFocusState(snapshot.focus ?? EMPTY_FOCUS)
  })

  const setFocus = useCallback(
    async (userId: string | null) => {
      const id = roomIdRef.current
      if (!id) return
      try {
        const { focus: next } = await roomExtrasApi.setFocus(id, userId)
        atRef.current = Date.now()
        setFocusState(next ?? EMPTY_FOCUS)
        if (room) await publishSnapshot(room, CHANNEL_TOPIC.focus, { v: 1, at: atRef.current, focus: next })
      } catch (err) {
        setError(err instanceof Error ? err.message : '焦点设置失败')
      }
    },
    [room],
  )

  return { focus, error, refresh, setFocus }
}
