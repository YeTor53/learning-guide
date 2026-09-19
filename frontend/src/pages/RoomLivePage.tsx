/** 交流页（`/rooms/:id/live`）—— 专注感。
 *
 * 设计事实源：docs/02-modules/r002-livekit-features.md §3 F-16、§4.1；redirect-04 §4.2；
 *             ADR-0011 条 4（外部调用）、§8.4 归因、§8.5a 准入判定、§8.9 重连、§8.10 设备保持、§8.11 专注态。
 * 口径：连接前**先取票**（服务端校验成员身份）→ 未获批不发连接请求；成功连接后由 SDK 驱动在场。
 */
import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, ArrowLeft, BellRing, Crosshair, Loader2, MonitorUp, PanelRightOpen, RotateCw } from 'lucide-react'
import { LiveKitRoom, RoomAudioRenderer } from '@livekit/components-react'

import { ApiError } from '../api/http'
import { livekitApi } from '../api/livekit'
import { roomsApi, type Member, type Role } from '../api/rooms'
import DeviceBar from '../components/live/DeviceBar'
import LiveStage from '../components/live/LiveStage'
import RoomSidePanel from '../components/live/RoomSidePanel'
import { useActiveSpeaker } from '../hooks/useActiveSpeaker'
import { useChatMessages } from '../hooks/useChatMessages'
import { useChromeIdle } from '../hooks/useChromeIdle'
import { useLocalDeviceState } from '../hooks/useLocalDeviceState'
import { useHandRaise } from '../hooks/useHandRaise'
import { useFocusRequests } from '../hooks/useFocusRequests'
import { useMicLevel } from '../hooks/useMicLevel'
import { useMicStates } from '../hooks/useMicStates'
import { useRosterSync } from '../hooks/useRosterSync'
import { useOnlineIdentities } from '../hooks/useOnlineIdentities'
import { useRoomConnection } from '../hooks/useRoomConnection'
import { useRoomFocus } from '../hooks/useRoomFocus'
import { useScreenShare } from '../hooks/useScreenShare'
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
  const [confirmingLeave, setConfirmingLeave] = useState(false)
  const [confirmingEnd, setConfirmingEnd] = useState(false)
  const [welcome, setWelcome] = useState(true)
  const [confirmingBack, setConfirmingBack] = useState(false)
  const [focusedSeconds, setFocusedSeconds] = useState(0)

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
  const micStates = useMicStates(connection.room) // r006：麦徽标的真实状态源（ADR-0017 D1）
  const micLevel = useMicLevel(connection.room, devices.micEnabled && connection.status === 'connected')
  const chromeIdle = useChromeIdle(CHROME_IDLE_SECONDS, Boolean(speaker))

  // r004（M3）：房内扩展能力。三者的「与库一致」由各自 hook 在 `connected` 时拉一次库保证（ADR-0013）
  const localIdentity = connection.room.localParticipant?.identity ?? ''
  const liveReady = connection.status === 'connected'
  const chat = useChatMessages(connection.room, id, liveReady)
  const hands = useHandRaise(connection.room, id, liveReady, localIdentity || null)
  const focus = useRoomFocus(connection.room, id, liveReady)
  // r009：焦点申请（协管 → 另一个非本人批准）与举手键的角色分流
  const canManage = myRole === 'host' || myRole === 'moderator'
  const focusRequests = useFocusRequests(id, liveReady, localIdentity || null, canManage)
  const iAmFocused = Boolean(focus.focus.subjectUserId && focus.focus.subjectUserId === localIdentity)
  const handLabel = iAmFocused
    ? '退出焦点'
    : myRole === 'host'
      ? '取得焦点'
      : myRole === 'moderator'
        ? (focusRequests.mine ? '已申请焦点' : '申请焦点')
        : undefined
  const handTitle = iAmFocused
    ? '退出焦点（把焦点让出来）'
    : myRole === 'host'
      ? '取得焦点（房主可直接取得）'
      : myRole === 'moderator'
        ? '申请焦点（需另一位管理身份批准）'
        : undefined
  const onHandControl = () => {
    if (iAmFocused) {
      void focus.setFocus(null)
      return
    }
    if (myRole === 'host') {
      void focus.setFocus(localIdentity || null)
      return
    }
    if (myRole === 'moderator') {
      void focusRequests.request_()
      return
    }
    void (hands.mine ? hands.lower() : hands.raise())
  }
  const screen = useScreenShare(connection.room, connection.status)

  // 未读：抽屉收起时累积，打开即清零（徽标只在状态条上，不弹 toast）
  const [unread, setUnread] = useState(0)
  const lastSeenRef = useRef(0)
  useEffect(() => {
    if (drawerOpen) {
      lastSeenRef.current = chat.messages.length
      setUnread(0)
      return
    }
    setUnread(Math.max(0, chat.messages.length - lastSeenRef.current))
  }, [chat.messages.length, drawerOpen])

  // 焦点失效提示（§8.7 边界态）：焦点对象不再是**在册**成员 → 派生时已回落，这里给 3 秒可见提示
  const focusMemberActive = Boolean(
    focus.focus.subjectUserId && members.some((m) => m.userId === focus.focus.subjectUserId && m.status === 'active'),
  )
  const [focusLost, setFocusLost] = useState(false)
  useEffect(() => {
    if (!focus.focus.subjectUserId || focusMemberActive) return
    setFocusLost(true)
    const timer = window.setTimeout(() => setFocusLost(false), 3_000)
    return () => window.clearTimeout(timer)
  }, [focus.focus.subjectUserId, focusMemberActive])

  // 协作式停止共享：收到房主/协管的请求 → 已自动停止，这里只提示一次
  useEffect(() => {
    if (screen.requestedBy) setNotice('房主请求你停止共享屏幕（已为你停止）')
  }, [screen.requestedBy])

  const isManager = myRole === 'host' || myRole === 'moderator'
  // 申请列表（真源）：只有管理者需要，5 秒轮询——门口有人等时要能立刻看到（修：原来误读了 messages，抽屉永远显示空）
  const requestsQuery = useQuery({
    queryKey: ['live-room-requests', id],
    queryFn: () => roomsApi.listRequests(id),
    enabled: isManager && Boolean(room),
    refetchInterval: 5_000,
    retry: false,
  })
  const pendingRequests = (requestsQuery.data ?? []).filter((item) => item.status === 'pending')
  const pendingCount = pendingRequests.length

  // 新申请到达 → 一次可见的提示（脉冲 + 状态条说明），不弹窗（redirect-03 未批前不引 toast）
  const [attention, setAttention] = useState(false)
  const [seenCount, setSeenCount] = useState(0)
  useEffect(() => {
    if (pendingCount > seenCount) {
      setAttention(true)
      const timer = window.setTimeout(() => setAttention(false), 2_400)
      setSeenCount(pendingCount)
      return () => window.clearTimeout(timer)
    }
    setSeenCount(pendingCount)
  }, [pendingCount, seenCount])

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
      // 未获准 → 送等待室（ADR-0012 修订 D7：这里不是错误，是流程）
      navigate(`/rooms/${id}/wait`, { replace: true })
    }
  }, [tokenQuery.error, navigate, id])

  // 进房仪式：欢迎行 3.2 秒后自动退场（建立「现在开始专注」的边界）
  useEffect(() => {
    const timer = window.setTimeout(() => setWelcome(false), 3200)
    return () => window.clearTimeout(timer)
  }, [])

  // 一起专注了多久（状态条右侧的安静计时，给正反馈而不是倒计时）
  useEffect(() => {
    if (connection.status !== 'connected') return
    const timer = window.setInterval(() => setFocusedSeconds((value) => value + 1), 1000)
    return () => window.clearInterval(timer)
  }, [connection.status])

  const focusedLabel = `${String(Math.floor(focusedSeconds / 60)).padStart(2, '0')}:${String(focusedSeconds % 60).padStart(2, '0')}`

  // Esc：先取消「确认离开 / 确认结束房间」，再收起抽屉（防呆：离场永远有退路）
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return
      if (confirmingLeave) setConfirmingLeave(false)
      else if (confirmingEnd) setConfirmingEnd(false)
      else if (confirmingBack) setConfirmingBack(false)
      else if (drawerOpen) setDrawerOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [confirmingLeave, confirmingEnd, confirmingBack, drawerOpen])

  const goBackToRooms = async () => {
    setConfirmingBack(false)
    if (connection.status === 'connected' || connection.status === 'reconnecting') await connection.disconnect()
    navigate('/')
  }

  const requestBack = () => {
    if (connection.status === 'connected' || connection.status === 'reconnecting') setConfirmingBack(true)
    else void goBackToRooms()
  }

  /** r006（ADR-0017 D2）：人数（房间详情）+ 待批（申请列表）一起重取 —— 别端动作与本端动作共用。 */
  const refreshRoster = () => {
    void queryClient.invalidateQueries({ queryKey: ['live-room', id] })
    void queryClient.invalidateQueries({ queryKey: ['live-room-requests', id] })
  }
  /** 本端做完房间动作后广播一次：让别端秒级跟上（收端在 useRosterSync 里）。 */
  const broadcastRoster = useRosterSync(connection.room, liveReady, refreshRoster)

  const doKick = async (userId: string) => {
    setBusyId(userId)
    try {
      const result = await livekitApi.kickMember(id, userId)
      setNotice(result.livekitApplied ? '已移出该成员' : '已移出该成员（实时断开未成功，对方可能仍在房间）')
      refreshRoster()
      void broadcastRoster()
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
      refreshRoster()
      void broadcastRoster()
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
      refreshRoster()
      void broadcastRoster()
    } catch (error) {
      setNotice(error instanceof ApiError ? error.message : '操作失败，请重试')
    } finally {
      setBusyId(null)
      setConfirming(null)
    }
  }

  const doLeave = async () => {
    setConfirmingLeave(false)
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

  /** 房主结束房间（r003）：成功后断开并回列表；失败保留连接与房间，只给提示。 */
  const doEnd = async () => {
    setConfirmingEnd(false)
    try {
      await roomsApi.end(id) // POST /api/rooms/{id}/end（r001 起存在；服务端含 delete_room 强制断开）
      await connection.disconnect()
      navigate('/')
    } catch (error) {
      setNotice(error instanceof ApiError ? error.message : '操作失败，请重试')
    }
  }

  const endedRoom = room?.status === 'ended'
  const fatalError = tokenQuery.error instanceof ApiError && tokenQuery.error.code === 'ROOM_ENDED'
  const fullError = tokenQuery.error instanceof ApiError && tokenQuery.error.code === 'ROOM_FULL'

  // 取票失败（满员等）→ 停留 4 秒把原因说清，然后回主界面（ADR-0012 修订 D6）
  useEffect(() => {
    if (!fullError) return
    const timer = window.setTimeout(() => navigate('/', { replace: true }), 4000)
    return () => window.clearTimeout(timer)
  }, [fullError, navigate])

  if (detail.isLoading) {
    return (
      <div className="card live-fallback">
        <Loader2 {...ICON} className="spin" />
        <span className="muted">正在进入房间…</span>
      </div>
    )
  }

  if (detail.isError || endedRoom || fatalError || fullError) {
    const title = fullError
      ? tokenQuery.error instanceof ApiError
        ? tokenQuery.error.message
        : '房间已满'
      : endedRoom || fatalError
        ? '房间已结束，仅可查看历史内容'
        : '无法进入这间房'
    return (
      <div className="card live-fallback">
        <AlertCircle size={22} strokeWidth={1.75} />
        <div>
          <p style={{ margin: '0 0 6px' }}>{title}</p>
          <p className="muted" style={{ margin: '0 0 10px', fontSize: 13 }}>
            {fullError ? '4 秒后自动回到房间列表' : '可以回房间列表看看别的讨论'}
          </p>
          <div style={{ display: 'flex', gap: 8 }}>
            <Link className="btn btn-sm" to="/">
              回房间列表
            </Link>
            <Link className="btn btn-ghost btn-sm" to="/">
              回房间列表
            </Link>
          </div>
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
            <button className="live-back" onClick={requestBack} title="回到房间列表">
              <ArrowLeft {...ICON} />
              房间列表
            </button>
            <span className="live-sep" aria-hidden />
            <span className="live-title">{room?.title ?? '交流页'}</span>
            {/* r005（ADR-0016）：人数按**在册成员**（本库）显示，与准入/列表卡同一口径；
                「此刻谁在线」看成员抽屉（那一列是 LiveKit 事件驱动的在场标记）。 */}
            <span className="live-quiet mono" title="本场已获准进场的人数（在册成员 / 上限）；此刻谁在线看「成员」抽屉">
              {room?.memberCount ?? 0} / {room?.capacity ?? 8} 成员
            </span>
            <span className="live-quiet mono">{room?.roomCode}</span>
            {connection.status === 'connected' && (
              <span className="live-focus-timer mono" title="你在房间里的时长">
                {focusedLabel}
              </span>
            )}
            {/* r004 §8.4：全局状态指示（抽屉收起时唯一能看到的地方）；共享优先，不并列 */}
            {focusLost ? (
              <span className="live-quiet mono">焦点已失效</span>
            ) : screen.ownerId ? (
              <span className="live-quiet mono" title="有人正在共享屏幕（共享画面占焦点格）">
                <MonitorUp size={14} strokeWidth={1.75} style={{ verticalAlign: -2, marginRight: 4 }} />
                共享 {members.find((m) => m.userId === screen.ownerId)?.displayName ?? screen.ownerId}
              </span>
            ) : focus.focus.subjectUserId ? (
              <span className="live-quiet mono" title="房主/协管指定的发言焦点">
                <Crosshair size={14} strokeWidth={1.75} style={{ verticalAlign: -2, marginRight: 4 }} />
                焦点 {focus.focus.subjectName ?? ''}
              </span>
            ) : null}
          </div>
          <div className="live-statusbar-right">
            <span className={`live-badge live-badge-${connection.status}`}>
              {connection.status === 'reconnecting' && <RotateCw {...ICON} className="spin" />}
              {STATUS_LABEL[connection.status]}
            </span>
            <button
              className={`live-drawer-toggle${pendingCount > 0 ? ' has-pending' : ''}${attention ? ' live-attention' : ''}`}
              aria-label={`讨论与成员${unread > 0 ? `，有 ${unread} 条未读消息` : ''}${pendingCount > 0 ? `，有 ${pendingCount} 条待处理申请` : ''}`}
              aria-expanded={drawerOpen}
              title={`讨论与成员${unread > 0 ? `（${unread} 条未读）` : ''}${pendingCount > 0 ? ` · 门口 ${pendingCount} 位在等` : ''}`}
              onClick={() => setDrawerOpen((open) => !open)}
            >
              <PanelRightOpen {...ICON} />
              讨论与成员
              {unread > 0 && <span className="live-toggle-badge">{unread > 9 ? '9+' : unread}</span>}
              {pendingCount > 0 && <span className="live-toggle-badge live-toggle-badge-warn">{pendingCount}</span>}
            </button>
          </div>
        </header>

        {isManager && pendingCount > 0 && !drawerOpen && (
          <div className="live-notice" role="status">
            <BellRing {...ICON} />
            门口有 {pendingCount} 位在等房主批准
            <button className="btn btn-sm" onClick={() => setDrawerOpen(true)}>
              去处理
            </button>
          </div>
        )}

        {connection.reason && (
          <div className="alert alert-warn live-alert" role="status">
            {connection.reason}
            <button className="btn btn-sm" onClick={() => window.location.reload()} style={{ marginLeft: 12 }}>
              重新连接
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

        {welcome && (
          <div className="live-welcome" role="status">
            已进入 · {room?.topicLabel ?? ''} · 上限 {room?.capacity ?? 8} 人
          </div>
        )}

        <main className="live-main">
          {room && (
            <LiveStage
              room={room}
              connected={connection.status === 'connected' || connection.status === 'reconnecting'}
              members={members}
              onlineIds={onlineIds}
              speakerIdentity={speaker?.identity ?? null}
              localIdentity={localIdentity}
              micStates={micStates}
              focusUserId={focus.focus.subjectUserId}
              screenOwnerId={screen.ownerId}
              sharing={screen.sharing}
              onStopShare={() => void screen.stop()}
              handIds={hands.hands.map((item) => item.userId)}
            />
          )}
          {drawerOpen && room && (
            <RoomSidePanel
              room={room}
              members={members}
              myRole={myRole}
              onlineIds={onlineIds}
              requests={requestsQuery.data ?? []}
              busyId={busyId}
              chat={chat}
              myUserId={localIdentity || null}
              hands={hands}
              focus={focus}
              focusRequests={focusRequests}
              screen={screen}
              onChatChanged={() => {
                lastSeenRef.current = chat.messages.length
                setUnread(0)
              }}
              onClose={() => setDrawerOpen(false)}
              onKick={(userId) => setConfirming({ userId, action: 'kick' })}
              onSetRole={doSetRole}
              onTransferHost={(userId) => setConfirming({ userId, action: 'transfer' })}
              onApprove={async (requestId) => {
                try {
                  await roomsApi.approve(requestId)
                  queryClient.invalidateQueries({ queryKey: ['live-room-requests', id] })
                  refreshRoster()
      void broadcastRoster()
                } catch (error) {
                  setNotice(error instanceof ApiError ? error.message : '操作失败，请重试')
                }
              }}
              onReject={async (requestId) => {
                try {
                  await roomsApi.reject(requestId)
                  queryClient.invalidateQueries({ queryKey: ['live-room-requests', id] })
                  refreshRoster()
      void broadcastRoster()
                } catch (error) {
                  setNotice(error instanceof ApiError ? error.message : '操作失败，请重试')
                }
              }}
            />
          )}
        </main>

        {confirmingBack && (
          <div className="live-confirm" role="dialog" aria-modal="true">
            <p style={{ margin: 0 }}>
              回到房间列表会<strong>离开当前讨论</strong>（音视频断开），确定吗？
            </p>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-primary btn-sm" onClick={() => void goBackToRooms()}>
                确认返回
              </button>
              <button className="btn btn-ghost btn-sm" onClick={() => setConfirmingBack(false)}>
                继续讨论（Esc）
              </button>
            </div>
          </div>
        )}

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
          micLevel={micLevel}
          isHost={myRole === 'host'}
          disabled={connection.status === 'connecting' || connection.status === 'reconnecting'}
          idle={chromeIdle}
          confirmingLeave={confirmingLeave}
          onToggleMic={() => void devices.toggleMic()}
          onToggleCam={() => void devices.toggleCam()}
          onRequestLeave={() => setConfirmingLeave(true)}
          onConfirmLeave={() => void doLeave()}
          onCancelLeave={() => setConfirmingLeave(false)}
          confirmingEnd={confirmingEnd}
          onRequestEnd={() => setConfirmingEnd(true)}
          onConfirmEnd={() => void doEnd()}
          onCancelEnd={() => setConfirmingEnd(false)}
          handRaised={hands.mine}
          handActive={iAmFocused || hands.mine}
          handLabel={handLabel}
          handTitle={handTitle}
          sharing={screen.sharing}
          onToggleHand={onHandControl}
          onToggleShare={() => void (screen.sharing ? screen.stop() : screen.start())}
        />
      </div>
    </LiveKitRoom>
  )
}
