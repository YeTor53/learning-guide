/** 连接状态机：idle → connecting → connected ⇄ reconnecting → closed。
 *
 * 设计事实源：docs/02-modules/r002-livekit.md §8.4（断开归因）、§8.9（重连）、§8.5a（未获批 → 等待页）。
 * 约定：归因**优先取 SDK 的 DisconnectReason**；网络层失败才用兜底文案。
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { DisconnectReason, Room, RoomEvent } from 'livekit-client'

export type ConnectionStatus = 'idle' | 'connecting' | 'connected' | 'reconnecting' | 'closed'

const REASON_TEXT: Partial<Record<DisconnectReason, string>> = {
  [DisconnectReason.PARTICIPANT_REMOVED]: '你已被移出房间',
  [DisconnectReason.ROOM_DELETED]: '房间已结束',
  [DisconnectReason.DUPLICATE_IDENTITY]: '同一账号已在别处进入本房间',
  [DisconnectReason.ROOM_CLOSED]: '房间已关闭',
}

export interface RoomConnection {
  room: Room
  status: ConnectionStatus
  /** 断开原因文案（我们的主动 disconnect 为 null）。 */
  reason: string | null
  error: string | null
  connect: (url: string, token: string) => Promise<void>
  disconnect: () => Promise<void>
}

export function useRoomConnection(): RoomConnection {
  const room = useMemo(
    () => new Room({ adaptiveStream: true, dynacast: true }),
    [],
  )
  const [status, setStatus] = useState<ConnectionStatus>('idle')
  const [reason, setReason] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const onReconnecting = () => setStatus('reconnecting')
    const onReconnected = () => {
      setStatus('connected')
      setReason(null)
    }
    const onDisconnected = (code?: DisconnectReason) => {
      setStatus('closed')
      if (code === undefined || code === DisconnectReason.CLIENT_INITIATED) {
        setReason(null) // 自己点的「离开房间」，不提示
        return
      }
      setReason(REASON_TEXT[code] ?? '连接已断开，请检查网络后重试')
    }
    room
      .on(RoomEvent.Reconnecting, onReconnecting)
      .on(RoomEvent.Reconnected, onReconnected)
      .on(RoomEvent.Disconnected, onDisconnected)
    return () => {
      room
        .off(RoomEvent.Reconnecting, onReconnecting)
        .off(RoomEvent.Reconnected, onReconnected)
        .off(RoomEvent.Disconnected, onDisconnected)
    }
  }, [room])

  // U15（r004）：dev-only 调试句柄 —— 断线/归因的**事件注入**测试与排障入口。
  // 只在开发构建挂载；生产构建里 `import.meta.env.DEV` 为 false，不会出现在产物中。
  useEffect(() => {
    if (!import.meta.env.DEV) return
    const holder = window as unknown as { __lgRoom?: Room | null }
    holder.__lgRoom = room
    return () => {
      holder.__lgRoom = null
    }
  }, [room])

  const connectedRef = useRef(false)

  const connect = useCallback(
    async (url: string, token: string) => {
      if (connectedRef.current) return
      connectedRef.current = true
      setStatus('connecting')
      setError(null)
      try {
        await room.connect(url, token)
        setStatus('connected')
        setReason(null)
      } catch (err) {
        connectedRef.current = false
        setStatus('closed')
        const message = err instanceof Error ? err.message : '实时服务暂时不可用，请稍后重试'
        setError(message.includes('full') ? '房间已满（上限 8 人）' : '实时服务暂时不可用，请稍后重试')
        throw err
      }
    },
    [room],
  )

  const disconnect = useCallback(async () => {
    connectedRef.current = false
    await room.disconnect()
    setStatus('closed')
    setReason(null)
  }, [room])

  return { room, status, reason, error, connect, disconnect }
}
