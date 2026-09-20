/** r012：管理后台数据（三列表 + 三动作）。
 *
 * 分页与筛选进 queryKey，翻页即取；动作成功后失效对应列表（审计也要跟着变）。
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { adminApi, type AdminRoomQuery, type AdminUserQuery } from '../api/admin'

export function useAdminRooms(query: AdminRoomQuery) {
  return useQuery({ queryKey: ['admin-rooms', query], queryFn: () => adminApi.rooms(query) })
}

export function useAdminUsers(query: AdminUserQuery) {
  return useQuery({ queryKey: ['admin-users', query], queryFn: () => adminApi.users(query) })
}

export function useAdminSummaries(query: { status?: string; limit?: number; offset?: number }) {
  return useQuery({ queryKey: ['admin-summaries', query], queryFn: () => adminApi.summaries(query) })
}

export function useAdminAudit(query: { limit?: number; offset?: number }) {
  return useQuery({ queryKey: ['admin-audit', query], queryFn: () => adminApi.audit(query) })
}

export function useAdminActions() {
  const queryClient = useQueryClient()
  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['admin-rooms'] })
    void queryClient.invalidateQueries({ queryKey: ['admin-summaries'] })
    void queryClient.invalidateQueries({ queryKey: ['admin-audit'] })
    void queryClient.invalidateQueries({ queryKey: ['rooms'] })
  }

  const endRoom = useMutation({ mutationFn: adminApi.endRoom, onSuccess: invalidate })
  const deleteRoom = useMutation({ mutationFn: adminApi.deleteRoom, onSuccess: invalidate })
  const regenerateSummary = useMutation({ mutationFn: adminApi.regenerateSummary, onSuccess: invalidate })

  return { endRoom, deleteRoom, regenerateSummary }
}
