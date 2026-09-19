/** 限时邀请接口（r008）。
 *
 * 设计事实源：`docs/rounds/r008-assignment-gaps/design.md` §3；口径「最长 1 分钟」（ADR-0019）。
 */
import { request } from './http'

export interface Invite {
  id: string
  roomId: string
  code: string
  expiresAt: string
  maxUses: number
  usedCount: number
  createdAt: string
  expired: boolean
}

export interface InviteAcceptResult {
  roomId: string
  created: boolean
  displayName: string | null
}

export const invitesApi = {
  /** 生成限时邀请码（Host/Moderator；默认 60 秒、1 次可用）。 */
  create: (roomId: string, ttlSeconds: number, maxUses: number) =>
    request<Invite>(`/api/rooms/${roomId}/invites`, {
      method: 'POST',
      body: JSON.stringify({ ttlSeconds, maxUses }),
    }),
  /** 房间的邀请列表（Host/Moderator）。 */
  list: (roomId: string) => request<{ invites: Invite[] }>(`/api/rooms/${roomId}/invites`),
  /** 凭码加入：直接成为在册成员（已在册时幂等）。 */
  accept: (code: string) => request<InviteAcceptResult>(`/api/invites/${encodeURIComponent(code)}/accept`, { method: 'POST' }),
}
