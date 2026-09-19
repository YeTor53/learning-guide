/** 协管焦点申请（r009）：申请 / 列出待批 / 批准 / 拒绝。
 *
 * 设计事实源：docs/rounds/r009-focus-system/design.md §3；口径见 ADR-0021 D2（必须另一个非本人批准）。
 * 实时性：先用轮询（8 秒）+ 自身动作后立即刷新；SSE 归 r011（好友与定向邀请那轮）。
 */
import { useCallback, useEffect, useRef, useState } from 'react'

import { ApiError } from '../api/http'
import { request } from '../api/http'

export interface FocusRequest {
  id: string
  roomId: string
  requesterId: string
  requesterName: string
  status: string
  decidedBy: string | null
  createdAt: string
  decidedAt: string | null
}

export interface FocusRequestsState {
  requests: FocusRequest[]
  mine: FocusRequest | null
  error: string | null
  refresh: () => Promise<void>
  request_: () => Promise<void>
  approve: (id: string) => Promise<void>
  reject: (id: string) => Promise<void>
}

const POLL_MS = 8000

export function useFocusRequests(roomId: string | null, enabled: boolean, myUserId: string | null, canManage: boolean): FocusRequestsState {
  const [requests, setRequests] = useState<FocusRequest[]>([])
  const [error, setError] = useState<string | null>(null)
  const mounted = useRef(true)

  const refresh = useCallback(async () => {
    if (!roomId || !enabled || !canManage) return
    try {
      const data = await request<{ requests: FocusRequest[] }>(`/api/rooms/${roomId}/focus-requests`)
      if (mounted.current) {
        setRequests(data.requests)
        setError(null)
      }
    } catch (err) {
      if (mounted.current) setError(err instanceof ApiError ? err.message : '读取焦点申请失败')
    }
  }, [roomId, enabled, canManage])

  useEffect(() => {
    mounted.current = true
    void refresh()
    if (!enabled || !canManage || !roomId) return () => { mounted.current = false }
    const timer = window.setInterval(() => void refresh(), POLL_MS)
    return () => {
      mounted.current = false
      window.clearInterval(timer)
    }
  }, [refresh, enabled, canManage, roomId])

  const request_ = useCallback(async () => {
    if (!roomId) return
    try {
      await request(`/api/rooms/${roomId}/focus-requests`, { method: 'POST' })
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '申请焦点失败')
    }
  }, [roomId])

  const decide = useCallback(
    async (id: string, action: 'approve' | 'reject') => {
      try {
        await request(`/api/focus-requests/${id}/${action}`, { method: 'POST' })
        await refresh()
        setError(null)
      } catch (err) {
        setError(err instanceof ApiError ? err.message : '操作失败')
      }
    },
    [refresh],
  )

  return {
    requests,
    mine: requests.find((item) => item.requesterId === myUserId) ?? null,
    error,
    refresh,
    request_,
    approve: (id: string) => decide(id, 'approve'),
    reject: (id: string) => decide(id, 'reject'),
  }
}
