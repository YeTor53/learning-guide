/** 等待室（`/rooms/:id/wait`）—— 温暖感。
 *
 * 设计事实源：docs/02-modules/r002-livekit-features.md §3 F-17、§4.4；ADR-0012 修订 D4/D6/D7。
 * 流程：申请后自动来到这里 → 等房主批准 → **获批自动进入**（无手动步骤）→ 失败（满员/结束/网络）回主界面。
 */
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { AlertCircle, ArrowLeft, Loader2, Undo2 } from 'lucide-react'

import { ApiError } from '../api/http'
import { roomsApi } from '../api/rooms'
import QuoteLine from '../components/QuoteLine'
import WaitTimeline from '../components/WaitTimeline'
import { useWaitingRoom } from '../hooks/useWaitingRoom'

const ICON = { size: 16, strokeWidth: 1.75 } as const
/** 获批后停留多久再自动进入（单点可调，与风格指南 §12.2 的 --wait-autoenter-delay 对应）。 */
const AUTO_ENTER_DELAY_MS = 1500
/** 失败提示停留多久后回主界面（ADR-0012 修订 D6）。 */
const FAIL_BACK_DELAY_MS = 3000

export default function WaitingPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { state, room, refetch, isFetching } = useWaitingRoom(id)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 获批 → 自动进入交流页（不点任何按钮）
  useEffect(() => {
    if (state !== 'approved') return
    const timer = window.setTimeout(() => navigate(`/rooms/${id}/live`, { replace: true }), AUTO_ENTER_DELAY_MS)
    return () => window.clearTimeout(timer)
  }, [state, id, navigate])

  // 失败/终态 → 停留几秒自动回主界面
  useEffect(() => {
    if (state !== 'ended' && !error) return
    const timer = window.setTimeout(() => navigate('/', { replace: true }), FAIL_BACK_DELAY_MS + 1500)
    return () => window.clearTimeout(timer)
  }, [state, error, navigate])

  const withdraw = async () => {
    setBusy(true)
    setError(null)
    try {
      const requests = await roomsApi.listRequests(id).catch(() => [])
      const pending = requests.find((item) => item.status === 'pending')
      if (!pending) throw new ApiError('NOT_FOUND', '找不到待批申请，请刷新后再试', 404)
      await roomsApi.withdraw(pending.id)
      queryClient.invalidateQueries({ queryKey: ['waiting-room', id] })
      refetch()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '撤回失败，请重试')
    } finally {
      setBusy(false)
    }
  }

  const reapply = async () => {
    setBusy(true)
    setError(null)
    try {
      await roomsApi.requestJoin(id, '')
      queryClient.invalidateQueries({ queryKey: ['waiting-room', id] })
      refetch()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '申请失败，请重试')
    } finally {
      setBusy(false)
    }
  }

  if (state === 'loading') {
    return (
      <div className="wait-shell">
        <div className="wait-card">
          <Loader2 {...ICON} className="spin" />
          <p className="muted" style={{ margin: 0 }}>正在读取房间状态…</p>
          <QuoteLine scene="patience" />
        </div>
      </div>
    )
  }

  if (state === 'error' || state === 'ended') {
    return (
      <div className="wait-shell">
        <div className="wait-card wait-card-quiet">
          <AlertCircle size={22} strokeWidth={1.75} />
          <p style={{ margin: 0 }}>{state === 'ended' ? '房间已结束，仅可查看历史内容' : '读不到这个房间（可能已被删除）'}</p>
          <button className="btn btn-sm" onClick={() => navigate('/', { replace: true })}>
            回房间列表
          </button>
        </div>
      </div>
    )
  }

  const pending = state === 'pending'
  const approved = state === 'approved'
  // 时间线只在真的有申请时点亮：未申请 / 被拒 / 已撤回 → 第 1 步且中性色
  const timelineCurrent = approved ? 2 : pending ? 1 : 0
  const timelineMuted = state === 'rejected' || state === 'withdrawn' || state === 'none'

  return (
    <div className="wait-shell">
      <div className="wait-glow" aria-hidden />
      <div className="wait-card">
        <p className="wait-lead">
          {approved
            ? '房主同意了，正在把你送进去'
            : pending
              ? '你已经在门口了，房主看到就会开门'
              : state === 'rejected'
                ? '这次没能加入：房主没有批准'
                : '这个房间还需要先申请'}
        </p>

        <WaitTimeline current={timelineCurrent} muted={timelineMuted} />

        {room && (
          <div className="wait-room">
            <span className="wait-room-title">{room.title}</span>
            <span className="muted" style={{ fontSize: 13 }}>
              {room.topicLabel} · 房主 {room.hostName} · 上限 {room.capacity} 人
            </span>
            {room.description && <span className="muted" style={{ fontSize: 13 }}>{room.description}</span>}
          </div>
        )}

        {/* redirect-02（Q2=2）：这里的操作引导改为名言；「进度」由上方 WaitTimeline 视觉承担，
            「能做什么」由下方按钮承担 */}
        {approved ? (
          <p className="wait-note">马上自动进入，不用点任何按钮</p>
        ) : (
          <QuoteLine scene={pending ? 'patience' : 'farewell'} />
        )}

        {error && (
          <p className="wait-note" style={{ color: 'var(--danger)' }}>{error}</p>
        )}

        <div className="wait-actions">
          {pending && (
            <button className="btn btn-ghost btn-sm" onClick={() => void withdraw()} disabled={busy}>
              <Undo2 {...ICON} />
              撤回申请
            </button>
          )}
          {(state === 'rejected' || state === 'withdrawn' || state === 'none') && (
            <button className="btn btn-primary btn-sm" onClick={() => void reapply()} disabled={busy}>
              重新申请
            </button>
          )}
          <button className="btn btn-ghost btn-sm" onClick={() => navigate('/')} disabled={busy}>
            <ArrowLeft {...ICON} />
            回房间列表
          </button>
          {isFetching && <span className="dim" style={{ fontSize: 12 }}>刷新中…</span>}
        </div>
      </div>
    </div>
  )
}
