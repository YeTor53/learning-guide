import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { roomsApi, type CreateRoomBody, type RoomListQuery, type RoomListResult } from '../api/rooms'

export function useRooms(query: RoomListQuery) {
  return useQuery<RoomListResult>({
    queryKey: ['rooms', query],
    queryFn: () => roomsApi.list(query),
  })
}

export function useCreateRoom() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateRoomBody) => roomsApi.create(body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['rooms'] }),
  })
}
