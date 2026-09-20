/** 群聊消息状态：进房拉历史 + 发送落库 + 广播去重合并（ADR-0013）。
 *
 * 设计事实源：docs/rounds/r004-room-extras/design.md §5.5
 * 一致性：库是唯一真相 —— 进房/重连后 `refresh()` 必拉；广播只做即时合并，按服务端 id 去重。
 *
 * **系统消息的补广播（r012 cp-8c）**：房内系统消息（`kind === 'system'`：「XX 加入了房间 / 被移出房间 /
 * 房间已结束 / 满员拒绝」等）由**服务端**写入，没有任何客户端会广播它，于是此前只有整页刷新才能看到
 * （真机实测：批准入房后 20 秒、切 tab、关开抽屉都不出现，只有 F5 才有）。
 * 现在改为：任何一次 `refresh()` 拉到「近 `SYSTEM_BROADCAST_WINDOW_MS` 内新出现且本端没见过的」系统消息，
 * 就复用 chat topic 补广播一条 —— 收到方仍按 id 去重合并，因此不会重复入列，也不会自激（已知 id 不再广播）。
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { Room } from 'livekit-client'

import { MESSAGE_LIMIT, roomExtrasApi } from '../api/roomExtras'
import type { Message } from '../api/rooms'
import { CHANNEL_TOPIC, publishSnapshot, useDataChannel } from './useDataChannel'

export interface PendingMessage {
  id: string
  body: string
  createdAt: string
  failed: boolean
}

export interface ChatState {
  messages: Message[]
  pending: PendingMessage[]
  hasMore: boolean
  loading: boolean
  error: string | null
  refresh: () => Promise<void>
  loadMore: () => Promise<void>
  send: (body: string) => Promise<boolean>
  retry: (pendingId: string) => Promise<boolean>
}

function merge(list: Message[], message: Message): Message[] {
  if (list.some((item) => item.id === message.id)) return list
  return [...list, message].sort((a, b) => a.createdAt.localeCompare(b.createdAt))
}

/** 新系统消息的补广播窗口：只播「刚发生」的，历史不重播（30 秒覆盖「批准→对方进房→其首次拉取」这一段）。 */
const SYSTEM_BROADCAST_WINDOW_MS = 30_000


export function useChatMessages(room: Room | null, roomId: string | null, enabled: boolean): ChatState {
  const [messages, setMessages] = useState<Message[]>([])
  const [pending, setPending] = useState<PendingMessage[]>([])
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const roomIdRef = useRef(roomId)
  roomIdRef.current = roomId
  const roomRef = useRef<Room | null>(room)
  roomRef.current = room
  /** 本端已入列过的消息 id：用来认「这次拉取才出现的新系统消息」，避免把历史系统消息重播一遍。 */
  const knownIdsRef = useRef<Set<string>>(new Set())

  const refresh = useCallback(async () => {
    const id = roomIdRef.current
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      const { messages: items } = await roomExtrasApi.listMessages(id)
      const known = knownIdsRef.current
      const freshSince = Date.now() - SYSTEM_BROADCAST_WINDOW_MS
      const target = roomRef.current
      if (target) {
        for (const item of items) {
          if (item.kind !== 'system' || known.has(item.id)) continue
          if (new Date(item.createdAt).getTime() < freshSince) continue
          void publishSnapshot(target, CHANNEL_TOPIC.chat, { v: 1, message: item })
        }
      }
      for (const item of items) known.add(item.id)
      setMessages(items)
      setHasMore(items.length >= MESSAGE_LIMIT)
    } catch (err) {
      setError(err instanceof Error ? err.message : '消息加载失败')
    } finally {
      setLoading(false)
    }
  }, [])

  // 连接成功（含首次进房与重连恢复）后拉一次库 —— 「刷新/重进与库一致」的保证
  useEffect(() => {
    if (enabled) void refresh()
  }, [enabled, refresh])

  useDataChannel<{ v: number; message: Message }>(room, CHANNEL_TOPIC.chat, ({ message }) => {
    setMessages((prev) => merge(prev, message))
  })

  const send = useCallback(
    async (body: string) => {
      const text = body.trim()
      const id = roomIdRef.current
      if (!text || !id) return false
      const localId = `local-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
      setPending((prev) => [...prev, { id: localId, body: text, createdAt: new Date().toISOString(), failed: false }])
      try {
        const { message } = await roomExtrasApi.sendMessage(id, text)
        setPending((prev) => prev.filter((item) => item.id !== localId))
        setMessages((prev) => merge(prev, message))
        if (room) await publishSnapshot(room, CHANNEL_TOPIC.chat, { v: 1, message })
        return true
      } catch (err) {
        setPending((prev) => prev.map((item) => (item.id === localId ? { ...item, failed: true } : item)))
        setError(err instanceof Error ? err.message : '消息发送失败')
        return false
      }
    },
    [room],
  )

  const retry = useCallback(
    async (pendingId: string) => {
      const target = pending.find((item) => item.id === pendingId)
      if (!target) return false
      setPending((prev) => prev.filter((item) => item.id !== pendingId))
      return send(target.body)
    },
    [pending, send],
  )

  const loadMore = useCallback(async () => {
    const id = roomIdRef.current
    const earliest = messages[0]
    if (!id || !earliest || earliest.id.startsWith('local-')) return
    setLoading(true)
    try {
      const { messages: older } = await roomExtrasApi.listMessages(id, earliest.id)
      setMessages((prev) => [...older, ...prev].filter((item, index, all) => all.findIndex((x) => x.id === item.id) === index))
      setHasMore(older.length >= MESSAGE_LIMIT)
    } catch (err) {
      setError(err instanceof Error ? err.message : '更早的消息加载失败')
    } finally {
      setLoading(false)
    }
  }, [messages])

  return { messages, pending, hasMore, loading, error, refresh, loadMore, send, retry }
}
