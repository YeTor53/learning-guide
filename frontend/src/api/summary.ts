/** 讨论纪要接口（r008）。
 *
 * 设计事实源：`docs/rounds/r008-assignment-gaps/design.md` §3；后端 `api/routers/summary.py`。
 */
import { request } from './http'

export interface SessionSummary {
  id: string
  roomId: string
  status: 'ready' | 'failed'
  provider: string
  model: string
  inputDigest: string
  content: string
  error: string | null
  createdBy: string | null
  createdAt: string
  updatedAt: string
}

export const summaryApi = {
  /** 查看纪要；未生成时 `summary` 为 null。 */
  get: (roomId: string) => request<{ summary: SessionSummary | null }>(`/api/rooms/${roomId}/summary`),
  /** 生成 / 重新生成（Host/Moderator）。 */
  generate: (roomId: string) => request<SessionSummary>(`/api/rooms/${roomId}/summary`, { method: 'POST' }),
}
