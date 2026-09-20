/** 管理后台接口（r012）：只有超管可调（服务端 401/403 强制）。
 *
 * 口径：查询参数 snake_case（与既有 `mine=` / `status=` 一致），出参 camelCase。
 */
import { request } from './http'

export interface AdminRoom {
  id: string
  title: string
  topicLabel: string
  status: string
  capacity: number
  roomCode: string
  hostId: string
  hostName: string
  memberCount: number
  pendingCount: number
  summaryStatus: string | null
  createdAt: string
  endedAt: string | null
}

export interface AdminUser {
  id: string
  email: string
  displayName: string
  role: string
  createdAt: string
  lastSeenAt: string | null
  activeRooms: number
  messageCount: number
  globalMessageCount: number
}

export interface AdminSummary {
  id: string
  roomId: string
  roomTitle: string
  status: string
  provider: string
  model: string
  contentLength: number
  error: string | null
  createdBy: string | null
  createdAt: string
  updatedAt: string
}

export interface AdminAudit {
  id: string
  actorId: string | null
  actorName: string | null
  action: string
  targetType: string
  targetId: string
  detail: Record<string, unknown>
  createdAt: string
}

export interface AdminPage<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

export type AdminRoomQuery = {
  status?: 'active' | 'ended'
  q?: string
  limit?: number
  offset?: number
}

export type AdminUserQuery = {
  q?: string
  online_only?: 0 | 1
  limit?: number
  offset?: number
}

function query(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '') search.set(key, String(value))
  })
  const text = search.toString()
  return text ? `?${text}` : ''
}

export const adminApi = {
  rooms: (params: AdminRoomQuery = {}) => request<AdminPage<AdminRoom>>(`/api/admin/rooms${query(params)}`),
  users: (params: AdminUserQuery = {}) => request<AdminPage<AdminUser>>(`/api/admin/users${query(params)}`),
  summaries: (params: { status?: string; limit?: number; offset?: number } = {}) =>
    request<AdminPage<AdminSummary>>(`/api/admin/summaries${query(params)}`),
  audit: (params: { action?: string; limit?: number; offset?: number } = {}) =>
    request<AdminPage<AdminAudit>>(`/api/admin/audit${query(params)}`),

  endRoom: (roomId: string) => request<Record<string, unknown>>(`/api/admin/rooms/${roomId}/end`, { method: 'POST' }),
  deleteRoom: (roomId: string) =>
    request<{ deleted: boolean; livekitApplied: boolean | null }>(`/api/admin/rooms/${roomId}`, { method: 'DELETE' }),
  regenerateSummary: (roomId: string) =>
    request<{ id: string; status: string; content: string }>(`/api/admin/rooms/${roomId}/summary`, { method: 'POST' }),
}
