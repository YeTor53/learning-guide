/** r013 回看页数据：房间详情 + 三源合一时间线 + 纪要（全部复用既有只读接口，无新端点）。
 *
 * 权限口径（r013 需求单 Q1=1）：房主 / 历史协管 / 超管 / **当时在册成员**（含已离开）可读；
 * 其他人的 403 由后端给（`transcripts._assert_can_read`、`summary.get_summary`），这里只翻译成 `forbidden`。
 * 失败分区化：某一段挂了不影响其余两段渲染（不整页白屏）。
 */
import { useQuery } from '@tanstack/react-query'

import { ApiError } from '../api/http'
import type { Member, Room } from '../api/rooms'
import { roomsApi } from '../api/rooms'
import type { SessionSummary } from '../api/summary'
import { summaryApi } from '../api/summary'
import type { ConversationItem } from '../api/transcripts'
import { transcriptsApi } from '../api/transcripts'

export interface ReplayState {
  room: Room | null
  members: Member[]
  timeline: ConversationItem[]
  summary: SessionSummary | null
  loading: boolean
  /** 无权限（非当时在册成员/管理身份）——时间线与纪要都会 403。 */
  forbidden: boolean
  errors: { room: string | null; timeline: string | null; summary: string | null }
}

function isForbidden(err: unknown): boolean {
  return err instanceof ApiError && (err.status === 403 || err.status === 401)
}

export function useReplay(roomId: string, enabled = true): ReplayState {
  const roomQuery = useQuery({ queryKey: ['replay-room', roomId], queryFn: () => roomsApi.detail(roomId), enabled })
  const lineQuery = useQuery({
    queryKey: ['replay-timeline', roomId],
    queryFn: () => transcriptsApi.conversation(roomId),
    enabled,
    retry: false,
  })
  const summaryQuery = useQuery({
    queryKey: ['replay-summary', roomId],
    queryFn: () => summaryApi.get(roomId),
    enabled,
    retry: false,
  })

  const roomDetail = roomQuery.data ?? null
  return {
    room: roomDetail?.room ?? null,
    members: roomDetail?.members ?? [],
    timeline: lineQuery.data?.items ?? [],
    summary: summaryQuery.data?.summary ?? null,
    loading: roomQuery.isLoading || lineQuery.isLoading || summaryQuery.isLoading,
    forbidden: isForbidden(lineQuery.error) || isForbidden(summaryQuery.error),
    errors: {
      room: roomQuery.error ? (roomQuery.error instanceof ApiError ? roomQuery.error.message : '房间加载失败') : null,
      timeline: lineQuery.error && !isForbidden(lineQuery.error)
        ? (lineQuery.error instanceof ApiError ? lineQuery.error.message : '时间线加载失败')
        : null,
      summary: summaryQuery.error && !isForbidden(summaryQuery.error)
        ? (summaryQuery.error instanceof ApiError ? summaryQuery.error.message : '纪要加载失败')
        : null,
    },
  }
}
