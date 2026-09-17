import {
  AlertTriangle,
  Archive,
  AlignLeft,
  CalendarClock,
  CheckCircle2,
  ClipboardList,
  Crown,
  DoorOpen,
  Hash,
  LogIn,
  MessageSquare,
  RefreshCw,
  Send,
  ShieldCheck,
  Undo2,
  UserRound,
  Users,
  X,
} from 'lucide-react'
import { useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'

import { ApiError } from '../api/http'
import { ROLE_LABEL } from '../api/rooms'
import JoinRequestList from '../components/JoinRequestList'
import MemberList from '../components/MemberList'
import { useRoomDetail } from '../hooks/useRoomDetail'
import { useSession } from '../hooks/useSession'

const ICON = { size: 14, strokeWidth: 1.75 } as const

const ROLE_ICON = {
  host: <Crown {...ICON} />,
  moderator: <ShieldCheck {...ICON} />,
  participant: <UserRound {...ICON} />,
} as const

function stamp(value: string) {
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

function clock(value: string) {
  return new Date(value).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
}

/** 房间详情（功能页 F-03~F-05、F-08、F-09、F-12）：头部 → 操作区 → 简介 → 成员 → 待批申请 → 最近消息。 */
export default function RoomDetailPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const { user } = useSession()
  const [message, setMessage] = useState('')
  const [showJoinForm, setShowJoinForm] = useState(false)
  const [busyId, setBusyId] = useState<string | null>(null)

  const { data, isLoading, isError, error, refetch, isFetching, requests, requestJoin, withdraw, approve, reject, leave, end } =
    useRoomDetail(id)

  const flash = (location.state as { flash?: string } | null)?.flash

  if (isLoading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div className="skeleton" style={{ height: 180 }} />
        <div className="skeleton" style={{ height: 120 }} />
      </div>
    )
  }

  if (isError || !data) {
    const detailError = error instanceof ApiError ? error : null
    const notFound = detailError?.status === 404
    return (
      <div className="card">
        <div className="alert" role="alert">
          <AlertTriangle size={16} strokeWidth={1.75} style={{ marginTop: 2, flex: '0 0 16px' }} />
          {notFound ? '房间不存在或已被移除。' : `房间加载失败：${detailError?.message ?? '连不上后端'}。`}
        </div>
        <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
          {!notFound && (
            <button className="btn" onClick={() => refetch()}>
              <RefreshCw {...ICON} />
              重试
            </button>
          )}
          <Link className="btn" to="/">
            返回列表
          </Link>
        </div>
      </div>
    )
  }

  const { room, members, messages } = data
  const isManager = room.myRole === 'host' || room.myRole === 'moderator'
  const ended = room.status === 'ended'
  const loginLink = `/login?returnTo=${encodeURIComponent(`/rooms/${room.id}`)}`
  const actionError = [requestJoin.error, withdraw.error, approve.error, reject.error, leave.error, end.error].find(
    (item) => item instanceof ApiError,
  )
  const activeCount = members.filter((item) => item.status === 'active').length

  const doApprove = (requestId: string) => {
    setBusyId(requestId)
    approve.mutate(requestId, {
      onSettled: () => setBusyId(null),
      onSuccess: (result) => window.alert(`已批准 ${result.member.displayName} 加入`),
    })
  }

  const doReject = (requestId: string) => {
    setBusyId(requestId)
    reject.mutate(requestId, { onSettled: () => setBusyId(null), onSuccess: () => window.alert('已拒绝该申请') })
  }

  const doLeave = () => {
    if (!window.confirm('离开后需要重新申请才能进入，确定离开吗？')) return
    leave.mutate(undefined, { onSuccess: () => window.alert('已离开房间') })
  }

  const doEnd = () => {
    if (
      !window.confirm(
        '结束这个房间？\n\n① 所有人被移出，需重新申请才能再进\n② 房间变为只读\n③ 系统会为这次讨论生成一份纪要',
      )
    )
      return
    end.mutate(undefined, { onSuccess: () => window.alert('房间已结束，现在是只读状态') })
  }

  return (
    <div>
      <div className="detail-head">
        {flash && (
          <div className="alert alert-info" style={{ marginBottom: 12 }}>
            <CheckCircle2 size={16} strokeWidth={1.75} style={{ marginTop: 2, flex: '0 0 16px' }} />
            {flash}
          </div>
        )}

        <div className="badges">
          <span className="chip chip-quiet">
            <Hash {...ICON} />
            {room.topicLabel}
          </span>
          {ended ? (
            <span className="chip chip-quiet">
              <Archive {...ICON} />
              已结束
            </span>
          ) : (
            <span className="chip chip-accent">{room.phase === 'active.in_session' ? `讨论中 · ${activeCount} 人` : '进行中'}</span>
          )}
          {room.myRole && (
            <span className="chip chip-accent">
              {ROLE_ICON[room.myRole]}
              {ROLE_LABEL[room.myRole]}
            </span>
          )}
        </div>

        <h1 className="detail-title">{room.title}</h1>

        <div className="meta-row">
          <span className="item">
            <Crown {...ICON} />
            房主 {room.hostName}
          </span>
          <span className="item">
            <CalendarClock {...ICON} />
            创建于 {stamp(room.createdAt)}
          </span>
          <span className="item mono">{room.roomCode}</span>
          <span className="item">
            <Users {...ICON} />
            {activeCount}/{room.capacity}
          </span>
          {room.endedAt && (
            <span className="item">
              <Archive {...ICON} />
              结束于 {stamp(room.endedAt)}
            </span>
          )}
        </div>

        <div className="actions" style={{ marginTop: 16 }}>
          {ended ? (
            <span className="dim" style={{ fontSize: 13 }}>
              房间已结束，仅可查看历史内容
            </span>
          ) : !user ? (
            <button className="btn btn-primary" onClick={() => navigate(loginLink)}>
              <LogIn {...ICON} size={16} />
              登录后加入
            </button>
          ) : room.myRole === 'participant' || room.myRole === 'moderator' ? (
            <>
              <span className="chip chip-accent">你已在房间中</span>
              <button className="btn" onClick={doLeave} disabled={leave.isPending}>
                <DoorOpen {...ICON} />
                离开房间
              </button>
            </>
          ) : room.myRole === 'host' ? (
            <>
              <span className="chip chip-accent">你是房主</span>
              <button className="btn btn-danger" onClick={doEnd} disabled={end.isPending}>
                <X {...ICON} />
                {end.isPending ? '结束中…' : '结束房间'}
              </button>
            </>
          ) : room.myRequestStatus === 'pending' ? (
            <>
              <span className="chip chip-warn">等待批准</span>
              <button
                className="btn"
                disabled={withdraw.isPending}
                onClick={() => {
                  const pending = requests.find((item) => item.userId === user.id)
                  if (pending) withdraw.mutate(pending.id, { onSuccess: () => window.alert('已撤回申请') })
                  else window.alert('撤回失败：找不到待批申请，请刷新后再试')
                }}
              >
                <Undo2 {...ICON} />
                撤回申请
              </button>
            </>
          ) : showJoinForm ? (
            <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: 8 }}>
              <textarea
                className="textarea"
                style={{ minHeight: 72 }}
                placeholder="简单介绍一下你的兴趣方向（可选）"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
              />
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  className="btn btn-primary"
                  disabled={requestJoin.isPending}
                  onClick={() =>
                    requestJoin.mutate(message, {
                      onSuccess: () => {
                        setShowJoinForm(false)
                        setMessage('')
                      },
                    })
                  }
                >
                  <Send {...ICON} />
                  {requestJoin.isPending ? '提交中…' : '提交申请'}
                </button>
                <button className="btn btn-ghost" onClick={() => setShowJoinForm(false)}>
                  取消
                </button>
              </div>
            </div>
          ) : (
            <button className="btn btn-primary" onClick={() => setShowJoinForm(true)}>
              <LogIn {...ICON} size={16} />
              申请加入
            </button>
          )}
          <div style={{ flex: 1 }} />
          <button className="btn btn-ghost btn-sm" onClick={() => refetch()} disabled={isFetching} title="手动刷新（每 5 秒自动刷新）">
            <RefreshCw {...ICON} size={13} />
            刷新
          </button>
        </div>

        {actionError instanceof ApiError && (
          <div className="alert" role="alert" style={{ marginTop: 12 }}>
            <AlertTriangle size={16} strokeWidth={1.75} style={{ marginTop: 2, flex: '0 0 16px' }} />
            {actionError.message}
          </div>
        )}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        <section className="panel">
          <div className="panel-title">
            <AlignLeft {...ICON} size={16} />
            简介
          </div>
          {room.description ? (
            <p style={{ whiteSpace: 'pre-wrap', margin: 0, color: 'var(--text-dim)' }}>{room.description}</p>
          ) : (
            <p className="dim" style={{ margin: 0 }}>
              房主没有写简介
            </p>
          )}
        </section>

        <section className="panel">
          <div className="panel-title">
            <Users {...ICON} size={16} />
            成员（{activeCount}/{room.capacity}）
          </div>
          <MemberList members={members} />
        </section>

        {isManager && (
          <section className="panel">
            <div className="panel-title">
              <ClipboardList {...ICON} size={16} />
              待处理申请
              {room.pendingCount > 0 && <span className="chip chip-warn">{room.pendingCount}</span>}
            </div>
            <JoinRequestList requests={requests} busyId={busyId} onApprove={doApprove} onReject={doReject} pendingOnly />
          </section>
        )}

        <section className="panel">
          <div className="panel-title">
            <MessageSquare {...ICON} size={16} />
            最近消息
            <span className="dim" style={{ fontSize: 12, fontWeight: 400 }}>
              最近 20 条 · 只读
            </span>
          </div>
          {messages.length === 0 ? (
            <p className="dim" style={{ margin: 0 }}>
              还没有人发言
            </p>
          ) : (
            <div className="timeline">
              {messages.map((item) => (
                <div className="msg" key={item.id}>
                  <span className="time">{clock(item.createdAt)}</span>
                  <span>
                    <span className="who">{item.displayName}</span>
                    <span className="muted">：{item.body}</span>
                  </span>
                </div>
              ))}
            </div>
          )}
          <p className="dim" style={{ marginTop: 16, marginBottom: 0, fontSize: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
            房间内实时收发消息属 M3；本轮只读展示历史消息。
            <Link to="/" style={{ color: 'var(--accent)' }}>
              返回列表
            </Link>
          </p>
        </section>
      </div>
    </div>
  )
}
