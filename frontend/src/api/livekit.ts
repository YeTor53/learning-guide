/** 实时房间接口（r002）：取 Token 与房间管理动作。
 *
 * 设计事实源：docs/02-modules/r002-livekit.md §5（4 条路由）、§6.8；错误码矩阵见 §8。
 * 约定：走既有 `request` 信封（失败抛 ApiError，`code` 直接用服务端语义码）。
 */
import { request } from './http'
import type { Member, Room, Role } from './rooms'

export interface RoomToken {
  token: string
  url: string
  roomName: string
  expiresIn: number
}

export interface KickResult {
  member: Member
  /** 外部（LiveKit）调用是否成功；false 表示库状态已改但对方可能还在房里（ADR-0011 条 4）。 */
  livekitApplied: boolean
}

export interface RoleUpdateResult {
  member: Member
}

export interface TransferHostResult {
  room: Room
  previousHost: Member
  newHost: Member
}

export const livekitApi = {
  /** 取进房 Token（服务端校验成员身份与房间状态；403 NOT_MEMBER / 409 ROOM_ENDED）。 */
  issueToken: (roomId: string) => request<RoomToken>(`/api/rooms/${roomId}/token`, { method: 'POST' }),

  /** 移出成员（Host 任意 / Moderator 只能移出普通成员）。 */
  kickMember: (roomId: string, userId: string) =>
    request<KickResult>(`/api/rooms/${roomId}/members/${userId}`, { method: 'DELETE' }),

  /** 任命 / 取消协管（仅 Host）。 */
  setMemberRole: (roomId: string, userId: string, role: Exclude<Role, 'host'>) =>
    request<RoleUpdateResult>(`/api/rooms/${roomId}/members/${userId}/role`, {
      method: 'PATCH',
      body: JSON.stringify({ role }),
    }),

  /** 移交房主（仅 Host）。 */
  transferHost: (roomId: string, userId: string) =>
    request<TransferHostResult>(`/api/rooms/${roomId}/transfer-host`, {
      method: 'POST',
      body: JSON.stringify({ userId }),
    }),
}
