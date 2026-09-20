/** r012 在线心跳接口。
 *
 * 口径：前端每 60 秒 `POST /api/presence`（design §2.6，Q14=2 短轮询）；后端写 `users.last_seen_at`，
 * 判据窗口由后端 `PRESENCE_ONLINE_SECONDS`（默认 120 秒）决定。前端不依赖返回值。
 */
import { request } from './http'

export interface PresenceBeat {
  ok: boolean
  lastSeenAt: string
}

export const presenceApi = {
  beat: () => request<PresenceBeat>('/api/presence', { method: 'POST' }),
}
