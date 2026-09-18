/** 取进房 Token 的 query（每次连接/重连都现签，ADR-0011 条 3）。 */
import { useQuery } from '@tanstack/react-query'

import { livekitApi } from '../api/livekit'

export function useRoomToken(roomId: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: ['room-token', roomId],
    queryFn: () => livekitApi.issueToken(roomId as string),
    enabled: enabled && Boolean(roomId),
    staleTime: 0, // Token 有 TTL，不允许复用缓存
    gcTime: 0,
    retry: false,
  })
}
