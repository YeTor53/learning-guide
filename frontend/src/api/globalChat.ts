/** 全服大屏聊天接口（r012）：未登录可读、登录可发（单条 ≤500 字）。 */
import { request } from './http'

export interface GlobalMessage {
  id: string
  userId: string
  displayName: string
  body: string
  authorOnline: boolean
  createdAt: string
}

export const GLOBAL_BODY_MAX = 500

export const globalChatApi = {
  list: (params: { limit?: number; beforeId?: string } = {}) => {
    const search = new URLSearchParams()
    if (params.limit) search.set('limit', String(params.limit))
    if (params.beforeId) search.set('before_id', params.beforeId)
    const text = search.toString()
    return request<{ items: GlobalMessage[] }>(`/api/global-messages${text ? `?${text}` : ''}`)
  },

  post: (body: string) =>
    request<GlobalMessage>('/api/global-messages', { method: 'POST', body: JSON.stringify({ body }) }),
}
