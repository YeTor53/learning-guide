/** r012：SSE 通知流（`GET /api/events`）。
 *
 * 口径（ADR-0025 D2/D3）：只推**通知型事件**，载荷最小（只有 id）；收到后照旧走 HTTP 拉真相。
 * 断线由浏览器 `EventSource` 自带重连（服务端首帧给 `retry: 3000`）；另有 30 秒轮询兜底（见 useGlobalChat）。
 */
import { useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'

export function useEventStream(enabled: boolean): void {
  const queryClient = useQueryClient()

  useEffect(() => {
    if (!enabled || typeof EventSource === 'undefined') return

    const source = new EventSource('/api/events')
    const onNotify = (raw: Event) => {
      const data = (raw as MessageEvent<string>).data
      try {
        const event = JSON.parse(data) as { type?: string }
        if (event.type === 'global_message') void queryClient.invalidateQueries({ queryKey: ['global-messages'] })
        if (event.type === 'room_changed' || event.type === 'admin_action') void queryClient.invalidateQueries({ queryKey: ['rooms'] })
      } catch {
        /* 载荷异常就忽略：HTTP 拉真相 + 轮询仍会兜底 */
      }
    }

    source.addEventListener('notify', onNotify)
    return () => {
      source.removeEventListener('notify', onNotify)
      source.close()
    }
  }, [enabled, queryClient])
}

export default useEventStream
