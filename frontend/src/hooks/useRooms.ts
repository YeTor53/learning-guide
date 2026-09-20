import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { roomsApi, type CreateRoomBody, type RoomListQuery, type RoomListResult } from '../api/rooms'

export function useRooms(query: RoomListQuery) {
  return useQuery<RoomListResult>({
    queryKey: ['rooms', query],
    queryFn: () => roomsApi.list(query),
    // r011 redirect-03：列表页此前**完全不刷新**（别人新建/结束的房间要手动刷才出现）。
    // 5 秒轮询 + 切回窗口立即刷新（main.tsx 的 refetchOnWindowFocus）。
    refetchInterval: 5_000,
  })
}

export function useCreateRoom() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateRoomBody) => roomsApi.create(body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['rooms'] }),
  })
}
