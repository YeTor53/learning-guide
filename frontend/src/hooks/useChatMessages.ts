/** 群聊消息状态：进房拉历史 + 发送落库 + 广播去重合并（ADR-0013）。
 *
 * 设计事实源：docs/rounds/r004-room-extras/design.md §5.5
 * 一致性：库是唯一真相 —— 进房/重连后 `refresh()` 必拉；广播只做即时合并，按服务端 id 去重。
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

export function useChatMessages(room: Room | null, roomId: string | null, enabled: boolean): ChatState {
  const [messages, setMessages] = useState<Message[]>([])
  const [pending, setPending] = useState<PendingMessage[]>([])
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const roomIdRef = useRef(roomId)
  roomIdRef.current = roomId

  const refresh = useCallback(async () => {
    const id = roomIdRef.current
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      const { messages: items } = await roomExtrasApi.listMessages(id)
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
