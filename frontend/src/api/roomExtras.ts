/** r004（M3）房内扩展能力的 HTTP 封装：消息 / 举手 / 焦点。
 *
 * 设计事实源：docs/rounds/r004-room-extras/design.md §4（接口契约）、§5.5
 * 口径（ADR-0013）：HTTP 落库是唯一真相；房内实时只做加速（见 hooks/useDataChannel.ts）。
 */
import { request } from './http'
import type { Message } from './rooms'

export interface Hand {
  id: string
  userId: string
  displayName: string
  raisedAt: string
}

export interface Focus {
  subjectUserId: string | null
  subjectName: string | null
  actorUserId: string | null
  setAt: string | null
}

export const MESSAGE_LIMIT = 50

export const roomExtrasApi = {
  listMessages: (roomId: string, before?: string, limit: number = MESSAGE_LIMIT) => {
    const params = new URLSearchParams({ limit: String(limit) })
    if (before) params.set('before', before)
    return request<{ messages: Message[] }>(`/api/rooms/${roomId}/messages?${params.toString()}`)
  },

  sendMessage: (roomId: string, body: string) =>
    request<{ message: Message }>(`/api/rooms/${roomId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ body }),
    }),

  listHands: (roomId: string) => request<{ hands: Hand[] }>(`/api/rooms/${roomId}/hand-raises`),

  raiseHand: (roomId: string) => request<{ hands: Hand[] }>(`/api/rooms/${roomId}/hand-raise`, { method: 'POST' }),

  lowerOwnHand: (roomId: string) => request<{ hands: Hand[] }>(`/api/rooms/${roomId}/hand-raise`, { method: 'DELETE' }),

  lowerOtherHand: (roomId: string, userId: string) =>
    request<{ hands: Hand[] }>(`/api/rooms/${roomId}/hand-raise/${userId}`, { method: 'DELETE' }),

  getFocus: (roomId: string) => request<{ focus: Focus }>(`/api/rooms/${roomId}/focus`),

  setFocus: (roomId: string, userId: string | null) =>
    request<{ focus: Focus }>(`/api/rooms/${roomId}/focus`, {
      method: 'POST',
      body: JSON.stringify({ userId }),
    }),
}
