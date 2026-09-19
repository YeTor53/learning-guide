import { request } from './http'
import type { User } from './auth'

export type RoomStatus = 'active' | 'ended'
export type Topic =
  | 'epicureanism'
  | 'math-biology'
  | 'german-history'
  | 'philosophy-history'
  | 'chinese-philosophy'
  | 'ethics'
  | 'modern-history'
  | 'ancient-china'
  | 'mathematical-analysis'
  | 'linear-algebra'
  | 'probability-statistics'
  | 'number-theory'
  | 'machine-learning'
  | 'custom'
export type Role = 'host' | 'moderator' | 'participant'
export type ExitReason = 'self_leave' | 'kicked' | 'room_ended'

export interface Room {
  id: string
  topic: Topic
  topicLabel: string
  title: string
  description: string
  status: RoomStatus
  phase: string
  capacity: number
  roomCode: string
  hostId: string
  hostName: string
  memberCount: number
  pendingCount: number
  myRole: Role | null
  myRequestStatus: string | null
  createdAt: string
  endedAt: string | null
}

export interface Member {
  id: string
  userId: string
  displayName: string
  role: Role
  status: 'active' | 'inactive'
  exitReason: ExitReason | null
  joinedAt: string
  leftAt: string | null
}

export interface Message {
  id: string
  userId: string
  displayName: string
  body: string
  kind: string
  createdAt: string
}

export interface JoinRequest {
  id: string
  roomId: string
  userId: string
  displayName: string
  message: string
  status: 'pending' | 'approved' | 'rejected' | 'withdrawn' | 'cancelled'
  createdAt: string
  decidedAt: string | null
  decidedBy: string | null
}

export interface RoomDetail {
  room: Room
  members: Member[]
  messages: Message[]
}

export interface RoomListQuery {
  status?: RoomStatus | 'all'
  topic?: Topic
  mine?: boolean
  limit?: number
  offset?: number
}

export interface RoomListResult {
  rooms: Room[]
  total: number
  limit: number
  offset: number
}

export interface CreateRoomBody {
  topic: Topic
  topicLabel: string
  title: string
  description: string
}

export const TOPIC_OPTIONS: { value: Topic; label: string; hint: string }[] = [
  // 顺序即展示顺序：前 3 项为保留的原有主题（r007 定），最后一项为「自定义」
  { value: 'epicureanism', label: '伊壁鸠鲁主义', hint: '从欲望清单到快乐主义' },
  { value: 'math-biology', label: '数理生物学', hint: '用模型解释生命现象' },
  { value: 'german-history', label: '德国史模拟', hint: '从帝国到分裂与统一' },
  { value: 'philosophy-history', label: '西方哲学史', hint: '从苏格拉底到康德' },
  { value: 'chinese-philosophy', label: '中国哲学', hint: '儒释道与心性之学' },
  { value: 'ethics', label: '伦理学', hint: '我们应当如何生活' },
  { value: 'modern-history', label: '世界近代史', hint: '大航海到两次大战' },
  { value: 'ancient-china', label: '中国古代史', hint: '先秦到明清' },
  { value: 'mathematical-analysis', label: '数学分析', hint: '极限、连续与微积分' },
  { value: 'linear-algebra', label: '线性代数', hint: '向量、矩阵与线性空间' },
  { value: 'probability-statistics', label: '概率论与数理统计', hint: '从随机到推断' },
  { value: 'number-theory', label: '数论', hint: '整数与素数的秩序' },
  { value: 'machine-learning', label: '机器学习基础', hint: '模型、损失与泛化' },
  { value: 'custom', label: '自定义', hint: '自己写一个主题名' },
]

export const ROLE_LABEL: Record<Role, string> = {
  host: '房主',
  moderator: '协管',
  participant: '成员',
}

export const EXIT_REASON_LABEL: Record<ExitReason, string> = {
  self_leave: '主动离开',
  kicked: '被移出',
  room_ended: '房间结束',
}

function toQuery(query: RoomListQuery): string {
  const params = new URLSearchParams()
  if (query.status) params.set('status', query.status)
  if (query.topic) params.set('topic', query.topic)
  if (query.mine) params.set('mine', '1')
  if (query.limit) params.set('limit', String(query.limit))
  if (query.offset) params.set('offset', String(query.offset))
  const qs = params.toString()
  return qs ? `?${qs}` : ''
}

export const roomsApi = {
  list: (query: RoomListQuery = {}) => request<RoomListResult>(`/api/rooms${toQuery(query)}`),

  create: (body: CreateRoomBody) => request<Room>('/api/rooms', { method: 'POST', body: JSON.stringify(body) }),

  detail: (roomId: string) => request<RoomDetail>(`/api/rooms/${roomId}`),

  requestJoin: (roomId: string, message: string) =>
    request<JoinRequest>(`/api/rooms/${roomId}/join-requests`, { method: 'POST', body: JSON.stringify({ message }) }),

  listRequests: (roomId: string, status?: string) =>
    request<{ requests: JoinRequest[] }>(
      `/api/rooms/${roomId}/join-requests${status ? `?status=${status}` : ''}`,
    ).then((r) => r.requests),

  approve: (requestId: string) =>
    request<{ request: JoinRequest; member: Member }>(`/api/join-requests/${requestId}/approve`, { method: 'POST' }),

  reject: (requestId: string) =>
    request<{ request: JoinRequest }>(`/api/join-requests/${requestId}/reject`, { method: 'POST' }),

  withdraw: (requestId: string) =>
    request<{ request: JoinRequest }>(`/api/join-requests/${requestId}/withdraw`, { method: 'POST' }),

  leave: (roomId: string) => request<Record<string, never>>(`/api/rooms/${roomId}/leave`, { method: 'POST' }),

  end: (roomId: string) => request<Room>(`/api/rooms/${roomId}/end`, { method: 'POST' }),
}

export type { User }
