/** r012：大屏消息（列表 + 发言 + 30 秒兜底轮询）。
 *
 * - 列表未登录也能看（公开面）；
 * - SSE 到达时由 `useEventStream` 失效 `['global-messages']`，这里只负责兜底轮询与发送；
 * - `refetchIntervalInBackground` 默认 false：窗口不在前台时不空跑。
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { globalChatApi } from '../api/globalChat'

/** 兜底轮询周期（毫秒）：SSE 断了也能看见新消息。 */
export const GLOBAL_CHAT_POLL_MS = 30_000
export const GLOBAL_CHAT_PAGE_SIZE = 50

export function useGlobalChat(enabled: boolean) {
  const queryClient = useQueryClient()

  const list = useQuery({
    queryKey: ['global-messages'],
    queryFn: () => globalChatApi.list({ limit: GLOBAL_CHAT_PAGE_SIZE }),
    enabled,
    refetchInterval: enabled ? GLOBAL_CHAT_POLL_MS : false,
    refetchIntervalInBackground: false,
  })

  const send = useMutation({
    mutationFn: (body: string) => globalChatApi.post(body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['global-messages'] }),
  })

  return {
    messages: list.data?.items ?? [],
    isLoading: list.isLoading,
    isError: list.isError,
    error: list.error,
    refetch: list.refetch,
    send,
  }
}
