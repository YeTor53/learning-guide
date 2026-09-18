/** 等待室的状态机（5 秒轮询）：等批准 → 已批准 → 自动进入。
 *
 * 设计事实源：docs/02-modules/r002-livekit-features.md §3 F-17、ADR-0012 修订 D4/D6。
 * 口径：申请不校验容量、批准不校验容量（容量闸在取票）；获批后**自动进入**，无手动步骤。
 */
import { useQuery } from '@tanstack/react-query'

import { roomsApi, type Room } from '../api/rooms'

const POLL_INTERVAL_MS = 5_000

export type WaitingState = 'loading' | 'error' | 'ended' | 'pending' | 'approved' | 'rejected' | 'withdrawn' | 'none'

export interface WaitingRoom {
  state: WaitingState
  room: Room | null
  refetch: () => void
  isFetching: boolean
}

export function useWaitingRoom(roomId: string, enabled = true): WaitingRoom {
  const query = useQuery({
    queryKey: ['waiting-room', roomId],
    queryFn: () => roomsApi.detail(roomId),
    enabled: enabled && Boolean(roomId),
    refetchInterval: POLL_INTERVAL_MS,
    retry: false,
  })

  const room = query.data?.room ?? null
  let state: WaitingState = 'loading'
  if (query.isError) state = 'error'
  else if (query.isLoading) state = 'loading'
  else if (!room) state = 'error'
  else if (room.status === 'ended') state = 'ended'
  else if (room.myRole) state = 'approved'
  else if (room.myRequestStatus === 'pending') state = 'pending'
  else if (room.myRequestStatus === 'rejected') state = 'rejected'
  else if (room.myRequestStatus === 'withdrawn' || room.myRequestStatus === 'cancelled') state = 'withdrawn'
  else state = 'none'

  return { state, room, refetch: () => void query.refetch(), isFetching: query.isFetching }
}
