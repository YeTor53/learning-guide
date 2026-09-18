/** 交流页（`/rooms/:id/live`）—— 专注感。
 *
 * 设计事实源：docs/02-modules/r002-livekit-features.md §3 F-16、§4.1；redirect-04 §4.2；
 *             ADR-0011 条 4（外部调用）、§8.4 归因、§8.5a 准入判定、§8.9 重连、§8.10 设备保持、§8.11 专注态。
 * 口径：连接前**先取票**（服务端校验成员身份）→ 未获批不发连接请求；成功连接后由 SDK 驱动在场。
 */
import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, Loader2, PanelRightOpen, RotateCw, Volume2 } from 'lucide-react'
import { LiveKitRoom, RoomAudioRenderer } from '@livekit/components-react'

import { ApiError } from '../api/http'
import { livekitApi } from '../api/livekit'
import { roomsApi, type Member, type Role } from '../api/rooms'
import DeviceBar from '../components/live/DeviceBar'
import LiveStage from '../components/live/LiveStage'
import RoomSidePanel from '../components/live/RoomSidePanel'
import { useActiveSpeaker } from '../hooks/useActiveSpeaker'
import { useChromeIdle } from '../hooks/useChromeIdle'
import { useLocalDeviceState } from '../hooks/useLocalDeviceState'
import { useOnlineIdentities } from '../hooks/useOnlineIdentities'
import { useRoomConnection } from '../hooks/useRoomConnection'
import { useRoomToken } from '../hooks/useRoomToken'

const ICON = { size: 16, strokeWidth: 1.75 } as const
/** 静默多少秒后界面退场（单点可调，与 global.css 的 --live-chrome-idle-seconds 保持一致）。 */
const CHROME_IDLE_SECONDS = 30

const STATUS_LABEL: Record<string, string> = {
  idle: '未连接',
  connecting: '正在连接…',
  connected: '已连接',
  reconnecting: '正在重连…',
  closed: '已断开',
}

export default function RoomLivePage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [confirming, setConfirming] = useState<{ userId: string; action: 'kick' | 'transfer' } | null>(null)

  const detail = useQuery({
    queryKey: ['live-room', id],
    queryFn: () => roomsApi.detail(id),
    staleTime: 30_000,
    retry: false,
  })
  const room = detail.data?.room
  const members: Member[] = detail.data?.members ?? []
  const myRole: Role | null = room?.myRole ?? null
  const canJoin = Boolean(room && room.status === 'active' && myRole)

  const tokenQuery = useRoomToken(id, canJoin)
  const connection = useRoomConnection()
  const speaker = useActiveSpeaker(connection.room)
  const devices = useLocalDeviceState(connection.room, connection.status)
  const onlineIds = useOnlineIdentities(connection.room, connection.status)
  const chromeIdle = useChromeIdle(CHROME_IDLE_SECONDS, Boolean(speaker))

  const requests = useMemo(() => detail.data?.messages ?? [], [detail.data])

  // 取票成功后再连接（不准入则压根不发连接请求）
  useEffect(() => {
    if (!tokenQuery.data || connection.status !== 'idle') return
    void connection.connect(tokenQuery.data.url, tokenQuery.data.token).catch(() => undefined)
  }, [tokenQuery.data, connection])

  // 准入判定：403 NOT_MEMBER → 回管理页（cp-r002-4 起改送等待页）；409 ROOM_ENDED → 房间已结束
  useEffect(() => {
    const error = tokenQuery.error
    if (!(error instanceof ApiError)) return
    if (error.status === 401) {
      navigate('/login', { replace: true })
      return
    }
    if (error.code === 'NOT_MEMBER' || error.status === 403) {
      navigate(`/rooms/${id}`, { replace: true, state: { notice: '你不在这个房间里（或已被移出），可以重新申请加入' } })
    }
  }, [tokenQuery.error, navigate, id])

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['live-room', id] })

  const doKick = async (userId: string) => {
    setBusyId(userId)
    try {
      const result = await livekitApi.kickMember(id, userId)
      setNotice(result.livekitApplied ? '已移出该成员' : '已移出该成员（实时断开未成功，对方可能仍在房间）')
      refresh()
    } catch (error) {
      setNotice(error instanceof ApiError ? error.message : '操作失败，请重试')
    } finally {
      setBusyId(null)
      setConfirming(null)
    }
  }

  const doSetRole = async (userId: string, role: Exclude<Role, 'host'>) => {
    setBusyId(userId)
    try {
      await livekitApi.setMemberRole(id, userId, role)
      setNotice(role === 'moderator' ? '已设为协管' : '已取消协管')
      refresh()
    } catch (error) {
      setNotice(error instanceof ApiError ? error.message : '操作失败，请重试')
    } finally {
      setBusyId(null)
    }
  }

  const doTransfer = async (userId: string) => {
    setBusyId(userId)
    try {
      await livekitApi.transferHost(id, userId)
      setNotice('已移交房主，你现在的角色是协管')
      refresh()
    } catch (error) {
      setNotice(error instanceof ApiError ? error.message : '操作失败，请重试')
    } finally {
      setBusyId(null)
      setConfirming(null)
    }
  }

  const doLeave = async () => {
    await connection.disconnect()
    if (myRole === 'host') {
      setNotice('房主不能直接离开，请先移交房主或结束房间')
      return
    }
    try {
      await roomsApi.leave(id)
    } catch {
      /* 已被移出等情形忽略：离开是幂等的用户体验动作 */
    }
    navigate(`/rooms/${id}`)
  }

  const endedRoom = room?.status === 'ended'
  const fatalError = tokenQuery.error instanceof ApiError && tokenQuery.error.code === 'ROOM_ENDED'

  if (detail.isLoading) {
    return (
      <div className="card live-fallback">
        <Loader2 {...ICON} className="spin" />
        <span className="muted">正在进入房间…</span>
      </div>
    )
  }

  if (detail.isError || endedRoom || fatalError) {
    return (
      <div className="card live-fallback">
        <AlertCircle size={22} strokeWidth={1.75} />
        <div>
          <p style={{ margin: '0 0 6px' }}>{endedRoom || fatalError ? '房间已结束，仅可查看历史内容' : '无法进入这间房'}</p>
          <Link className="btn btn-sm" to={`/rooms/${id}`}>
            回到房间管理
          </Link>
        </div>
      </div>
    )
  }

  return (
    <LiveKitRoom
        room={connection.room}
        serverUrl={tokenQuery.data?.url ?? ''}
        token={tokenQuery.data?.token ?? ''}
        connect={false}
        audio={false}
        video={false}
      >
      <RoomAudioRenderer />
      <div className={`live-shell${chromeIdle ? ' live-chrome-idle' : ''}`}>
        <header className="live-statusbar">
          <div className="live-statusbar-left">
            <Link className="live-title" to={`/rooms/${id}`} title="回到房间管理">
              {room?.title ?? '交流页'}
            </Link>
            <span className="dim mono">{members.filter((m) => m.status === 'active').length} / {room?.capacity ?? 8}</span>
            <span className="dim mono">{room?.roomCode}</span>
          </div>
          <div className="live-statusbar-right">
            <span className={`live-badge live-badge-${connection.status}`}>
              {connection.status === 'reconnecting' && <RotateCw {...ICON} className="spin" />}
              {STATUS_LABEL[connection.status]}
            </span>
            <button className="icon-btn" title="成员与管理" aria-label="成员与管理" onClick={() => setDrawerOpen((open) => !open)}>
              <PanelRightOpen {...ICON} />
            </button>
          </div>
        </header>

        {connection.reason && (
          <div className="alert alert-warn live-alert" role="status">
            {connection.reason}
            <button className="btn btn-sm" onClick={() => window.location.reload()} style={{ marginLeft: 12 }}>
              重新进入
            </button>
          </div>
        )}
        {notice && (
          <div className="alert live-alert" role="status">
            {notice}
            <button className="btn btn-ghost btn-sm" onClick={() => setNotice(null)} style={{ marginLeft: 12 }}>
              知道了
            </button>
          </div>
        )}
        {connection.error && <div className="alert alert-warn live-alert">{connection.error}</div>}

        {room && !room.memberCount ? null : null}

        <main className="live-main">
          <LiveStage members={members} speakerIdentity={speaker?.identity ?? null} localIdentity={connection.room.localParticipant?.identity ?? ''} />
          {drawerOpen && room && (
            <RoomSidePanel
              room={room}
              members={members}
              myRole={myRole}
              onlineIds={onlineIds}
              requests={requests.filter((item) => item.kind === 'request') as never}
              busyId={busyId}
              onKick={(userId) => setConfirming({ userId, action: 'kick' })}
              onSetRole={doSetRole}
              onTransferHost={(userId) => setConfirming({ userId, action: 'transfer' })}
              onApprove={async (requestId) => {
                try {
                  await roomsApi.approve(requestId)
                  refresh()
                } catch (error) {
                  setNotice(error instanceof ApiError ? error.message : '操作失败，请重试')
                }
              }}
              onReject={async (requestId) => {
                try {
                  await roomsApi.reject(requestId)
                  refresh()
                } catch (error) {
                  setNotice(error instanceof ApiError ? error.message : '操作失败，请重试')
                }
              }}
            />
          )}
        </main>

        {confirming && (
          <div className="live-confirm" role="dialog" aria-modal="true">
            <p style={{ margin: 0 }}>
              {confirming.action === 'kick' ? '确认移出该成员？移出后对方会立刻断开。' : '确认把房主移交给该成员？你将成为协管。'}
            </p>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                className={confirming.action === 'kick' ? 'btn btn-danger btn-sm' : 'btn btn-primary btn-sm'}
                onClick={() => (confirming.action === 'kick' ? doKick(confirming.userId) : doTransfer(confirming.userId))}
              >
                确认
              </button>
              <button className="btn btn-ghost btn-sm" onClick={() => setConfirming(null)}>
                取消
              </button>
            </div>
          </div>
        )}

        <DeviceBar
          micEnabled={devices.micEnabled}
          camEnabled={devices.camEnabled}
          idle={chromeIdle}
          onToggleMic={() => void devices.toggleMic()}
          onToggleCam={() => void devices.toggleCam()}
          onLeave={() => void doLeave()}
        />

        <p className="live-hint">
          <Volume2 {...ICON} /> 界面会在你静默 {CHROME_IDLE_SECONDS} 秒后自动淡出，动一下鼠标即回来
        </p>
      </div>
    </LiveKitRoom>
  )
}
