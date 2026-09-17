import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { roomsApi, type RoomDetail } from '../api/rooms'

/** 详情页 5 秒轮询：接入实时通道后改为推送（当前实现见 docs/02-modules/r001-rooms-features.md F-03）。 */
const POLL_INTERVAL_MS = 5_000

export function useRoomDetail(roomId: string) {
  const queryClient = useQueryClient()
  const detailQuery = useQuery<RoomDetail>({
    queryKey: ['room', roomId],
    queryFn: () => roomsApi.detail(roomId),
    refetchInterval: POLL_INTERVAL_MS,
  })

  const requestsQuery = useQuery({
    queryKey: ['room-requests', roomId],
    queryFn: () => roomsApi.listRequests(roomId),
    enabled: detailQuery.data?.room.myRole === 'host' || detailQuery.data?.room.myRole === 'moderator',
    refetchInterval: POLL_INTERVAL_MS,
  })

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['room', roomId] })
    queryClient.invalidateQueries({ queryKey: ['room-requests', roomId] })
    queryClient.invalidateQueries({ queryKey: ['rooms'] })
  }

  const requestJoin = useMutation({
    mutationFn: (message: string) => roomsApi.requestJoin(roomId, message),
    onSuccess: refresh,
  })
  const withdraw = useMutation({ mutationFn: (requestId: string) => roomsApi.withdraw(requestId), onSuccess: refresh })
  const approve = useMutation({ mutationFn: (requestId: string) => roomsApi.approve(requestId), onSuccess: refresh })
  const reject = useMutation({ mutationFn: (requestId: string) => roomsApi.reject(requestId), onSuccess: refresh })
  const leave = useMutation({ mutationFn: () => roomsApi.leave(roomId), onSuccess: refresh })
  const end = useMutation({ mutationFn: () => roomsApi.end(roomId), onSuccess: refresh })

  return {
    ...detailQuery,
    requests: requestsQuery.data ?? [],
    requestsLoading: requestsQuery.isLoading,
    requestJoin,
    withdraw,
    approve,
    reject,
    leave,
    end,
  }
}
