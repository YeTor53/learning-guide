import { useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'

import { ApiError } from '../api/http'
import { ROLE_LABEL } from '../api/rooms'
import JoinRequestList from '../components/JoinRequestList'
import MemberList from '../components/MemberList'
import { useRoomDetail } from '../hooks/useRoomDetail'
import { useSession } from '../hooks/useSession'

function formatTime(value: string) {
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

function clock(value: string) {
  return new Date(value).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
}

export default function RoomDetailPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const { user } = useSession()
  const [message, setMessage] = useState('')
  const [showJoinForm, setShowJoinForm] = useState(false)
  const [busyId, setBusyId] = useState<string | null>(null)

  const {
    data,
    isLoading,
    isError,
    refetch,
    requests,
    requestJoin,
    withdraw,
    approve,
    reject,
    leave,
    end,
  } = useRoomDetail(id)

  const flash = (location.state as { flash?: string } | null)?.flash

  if (isLoading) return <p className="muted">加载中…</p>
  if (isError || !data) {
    return (
      <div className="card">
        <div className="errorbar">房间加载失败：可能房间不存在，或后端未启动</div>
        <button style={{ marginTop: 8 }} onClick={() => refetch()}>
          重试
        </button>
      </div>
    )
  }

  const { room, members, messages } = data
  const isManager = room.myRole === 'host' || room.myRole === 'moderator'
  const loginLink = `/login?returnTo=${encodeURIComponent(`/rooms/${room.id}`)}`
  const actionError = [requestJoin.error, withdraw.error, approve.error, reject.error, leave.error, end.error].find(
    (item) => item instanceof ApiError,
  )

  const doApprove = (requestId: string) => {
    setBusyId(requestId)
    approve.mutate(requestId, {
      onSettled: () => setBusyId(null),
      onSuccess: (result) => window.alert(`已批准 ${result.member.displayName} 加入`),
    })
  }

  const doReject = (requestId: string) => {
    setBusyId(requestId)
    reject.mutate(requestId, {
      onSettled: () => setBusyId(null),
      onSuccess: () => window.alert('已拒绝该申请'),
    })
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
    <div className="stack">
      {flash && <div className="card" style={{ background: '#eff6ff', borderColor: '#bfdbfe' }}>{flash}</div>}

      <section className="card stack">
        <div className="row">
          <span className="badge">{room.topicLabel}</span>
          <span className={`badge ${room.status === 'ended' ? 'ended' : 'active'}`}>
            {room.status === 'ended' ? '已结束' : room.phase === 'active.in_session' ? `讨论中 · ${room.memberCount} 人` : '进行中'}
          </span>
          {room.myRole && <span className="badge me">我的角色：{ROLE_LABEL[room.myRole]}</span>}
        </div>
        <h1 style={{ margin: 0 }}>{room.title}</h1>
        <div className="muted">
          房主 {room.hostName} · 创建于 {formatTime(room.createdAt)} · 房间码 {room.roomCode}
          {room.endedAt && <> · 结束于 {formatTime(room.endedAt)}</>}
        </div>

        {actionError instanceof ApiError && <div className="errorbar">{actionError.message}</div>}

        <div className="row" style={{ flexWrap: 'wrap' }}>
          {room.status === 'ended' ? (
            <span className="muted">房间已结束，仅可查看历史内容</span>
          ) : !user ? (
            <button className="primary" onClick={() => navigate(loginLink)}>
              登录后加入
            </button>
          ) : room.myRole === 'participant' || room.myRole === 'moderator' ? (
            <>
              <span className="muted">你已在房间中</span>
              <button onClick={doLeave} disabled={leave.isPending}>
                离开房间
              </button>
            </>
          ) : room.myRole === 'host' ? (
            <>
              <span className="muted">你是房主</span>
              <button className="danger" onClick={doEnd} disabled={end.isPending}>
                {end.isPending ? '结束中…' : '结束房间'}
              </button>
            </>
          ) : room.myRequestStatus === 'pending' ? (
            <>
              <span className="badge me">等待批准</span>
              <button
                onClick={() => {
                  const pending = requests.find((item) => item.userId === user.id)
                  if (pending) withdraw.mutate(pending.id, { onSuccess: () => window.alert('已撤回申请') })
                  else window.alert('撤回失败：找不到待批申请，请刷新后再试')
                }}
                disabled={withdraw.isPending}
              >
                撤回申请
              </button>
            </>
          ) : showJoinForm ? (
            <div className="stack" style={{ width: '100%' }}>
              <textarea
                rows={2}
                placeholder="简单介绍一下你的兴趣方向（可选）"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
              />
              <div className="row">
                <button
                  className="primary"
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
                  {requestJoin.isPending ? '提交中…' : '提交申请'}
                </button>
                <button onClick={() => setShowJoinForm(false)}>取消</button>
              </div>
            </div>
          ) : (
            <button className="primary" onClick={() => setShowJoinForm(true)}>
              申请加入
            </button>
          )}
        </div>
      </section>

      <section className="card">
        <h3>简介</h3>
        <p style={{ whiteSpace: 'pre-wrap' }}>{room.description || <span className="muted">房主没有写简介</span>}</p>
      </section>

      <section className="card">
        <h3>成员（{members.filter((item) => item.status === 'active').length}/{room.capacity}）</h3>
        <MemberList members={members} />
      </section>

      {isManager && (
        <section className="card">
          <h3>
            待处理申请 {room.pendingCount > 0 && <span className="badge me">{room.pendingCount}</span>}
          </h3>
          <JoinRequestList requests={requests} busyId={busyId} onApprove={doApprove} onReject={doReject} pendingOnly />
        </section>
      )}

      <section className="card">
        <h3>最近消息（最近 20 条）</h3>
        {messages.length === 0 ? (
          <p className="muted">还没有人发言</p>
        ) : (
          <div className="messages">
            {messages.map((item) => (
              <div className="msg" key={item.id}>
                <span className="time">[{clock(item.createdAt)}]</span>
                <span>
                  <strong>{item.displayName}：</strong>
                  {item.body}
                </span>
              </div>
            ))}
          </div>
        )}
        <p className="muted" style={{ marginTop: 8 }}>
          房间内实时收发消息属 M3；本轮只读展示历史消息。<Link to="/">返回列表</Link>
        </p>
      </section>
    </div>
  )
}
