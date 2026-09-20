/** 连接状态机：idle → connecting → connected ⇄ reconnecting → closed。
 *
 * 设计事实源：docs/02-modules/r002-livekit.md §8.4（断开归因）、§8.9（重连）、§8.5a（未获批 → 等待页）。
 * 约定：归因**优先取 SDK 的 DisconnectReason**；网络层失败才用兜底文案。
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { DisconnectReason, Room, RoomEvent } from 'livekit-client'

export type ConnectionStatus = 'idle' | 'connecting' | 'connected' | 'reconnecting' | 'closed'

/** r013 cp-14：真终态（不自愈）——其余一切断开都当作「可恢复」（口径：界面无论如何不显示已断开）。 */
const TERMINAL_REASONS = new Set<DisconnectReason | undefined>([
  DisconnectReason.PARTICIPANT_REMOVED,
  DisconnectReason.ROOM_DELETED,
  DisconnectReason.ROOM_CLOSED,
  DisconnectReason.DUPLICATE_IDENTITY,
])

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
  /** r013 cp-11：本次断开是「页面被浏览器挂起（freeze/pagehide）」导致的，页面回到可见时应自动重连。 */
  autoDisconnected: boolean
  /** r013 cp-14：无需归因的自愈判定 —— 只要不是用户主动离开、也不是被移出/房间结束/同账号他处进入，就自愈。 */
  recoverable: boolean
  connect: (url: string, token: string) => Promise<void>
  disconnect: () => Promise<void>
}

export function useRoomConnection(): RoomConnection {
  const room = useMemo(
    () => new Room({ adaptiveStream: true, dynacast: true }),
    [],
  )
  // r013 cp-11：LiveKit SDK 对 `freeze`（Chrome 冻结隐藏/离屏页面时派发）**无条件**挂 onPageLeave，
  // 且它会走 ClientInitiated 断开（原因文案为 null）→ 表现成「隐藏就断、还没有提示、也不自愈」。
  // 这里自己先记一笔，把它与「用户点离开」区分开。
  const pageSuspendedRef = useRef(false)
  const userClosedRef = useRef(false)
  const terminalRef = useRef(false)
  const [autoDisconnected, setAutoDisconnected] = useState(false)
  const [status, setStatus] = useState<ConnectionStatus>('idle')
  const [reason, setReason] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const markSuspended = () => {
      pageSuspendedRef.current = true
    }
    window.addEventListener('freeze', markSuspended)
    window.addEventListener('pagehide', markSuspended)
    const onReconnecting = () => setStatus('reconnecting')
    // 信号级中断（WS 掉线）也要进 reconnecting：SDK 认为「用户多半察觉不到」，
    // 但 r002 §8.9 的契约是「断网 1~3 秒内状态条可见 + 控制坞禁用」，所以这里必须接。
    const onSignalReconnecting = () => setStatus('reconnecting')
    const onReconnected = () => {
      setStatus('connected')
      setReason(null)
    }
    const onDisconnected = (code?: DisconnectReason) => {
      // 口径（r013 cp-14，你定：界面不管怎样都不许显示「已断开」）：
      //   · 用户点「离开房间」 → closed，不提示、不自愈
      //   · 真终态（被移出 / 房间结束 / 同账号他处进入）→ closed + 原因文案
      //   · 其余一切（CLIENT_INITIATED / 无原因 / 浏览器冻结挂起 / 网络中断）→ 一律按「正在重连…」处理，
      //     由页面层不限次数重连，回来了就一切照旧。
      connectedRef.current = false
      terminalRef.current = TERMINAL_REASONS.has(code)
      if (userClosedRef.current) {
        setStatus('closed')
        setReason(null)
        return
      }
      if (terminalRef.current) {
        setStatus('closed')
        setReason((code !== undefined ? REASON_TEXT[code] : undefined) ?? '连接已断开，请检查网络后重试')
        return
      }
      pageSuspendedRef.current = false
      setAutoDisconnected(true)
      setStatus('reconnecting')
      setReason(null)
    }

    room
      .on(RoomEvent.Reconnecting, onReconnecting)
      .on(RoomEvent.SignalReconnecting, onSignalReconnecting)
      .on(RoomEvent.Reconnected, onReconnected)
      .on(RoomEvent.Disconnected, onDisconnected)
    return () => {
      window.removeEventListener('freeze', markSuspended)
      window.removeEventListener('pagehide', markSuspended)
      room
        .off(RoomEvent.Reconnecting, onReconnecting)
        .off(RoomEvent.SignalReconnecting, onSignalReconnecting)
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
      userClosedRef.current = false
      try {
        await room.connect(url, token)
        setStatus('connected')
        setReason(null)
        setAutoDisconnected(false)
      } catch (err) {
        connectedRef.current = false
        // 非用户主动的中断不进「已断开」：保持「正在重连…」，交给自愈循环继续试
        if (userClosedRef.current) setStatus('closed')
        const message = err instanceof Error ? err.message : '实时服务暂时不可用，请稍后重试'
        setError(message.includes('full') ? '房间已满（上限 8 人）' : '实时服务暂时不可用，请稍后重试')
        throw err
      }
    },
    [room],
  )

  const disconnect = useCallback(async () => {
    connectedRef.current = false
    pageSuspendedRef.current = false
    userClosedRef.current = true
    setAutoDisconnected(false)
    await room.disconnect()
    setStatus('closed')
    setReason(null)
  }, [room])

  const recoverable =
    (status === 'closed' || status === 'reconnecting') &&
    !userClosedRef.current &&
    !terminalRef.current

  return { room, status, reason, error, autoDisconnected, recoverable, connect, disconnect }
}
