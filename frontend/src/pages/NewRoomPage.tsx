import { LogIn, Sparkles } from 'lucide-react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import QuoteLine from '../components/QuoteLine'
import RoomForm from '../components/RoomForm'
import { useSession } from '../hooks/useSession'
import { useCreateRoom } from '../hooks/useRooms'
import { safeReturnTo } from './LoginPage'

export default function NewRoomPage() {
  const { user, isLoading } = useSession()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const returnTo = safeReturnTo(params.get('returnTo') ?? '/rooms/new')
  const createRoom = useCreateRoom()

  if (isLoading) return <div className="skeleton" style={{ height: 240 }} />

  if (!user) {
    return (
      <div className="card" style={{ maxWidth: 520, margin: '0 auto', textAlign: 'center' }}>
        <div className="empty" style={{ border: 'none' }}>
          <span className="icon-ring">
            <LogIn size={20} strokeWidth={1.75} />
          </span>
          <h2 style={{ fontSize: 22 }}>需要先登录</h2>
          <p className="muted" style={{ margin: 0 }}>
            创建房间需要账号：登录后你会直接回到这个页面。
          </p>
          <button className="btn btn-primary" onClick={() => navigate(`/login?returnTo=${encodeURIComponent(returnTo)}`)}>
            <LogIn size={16} strokeWidth={1.75} />
            去登录
          </button>
        </div>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 640 }}>
      <span className="kicker">
        <Sparkles size={13} strokeWidth={1.75} />
        New room
      </span>
      <h1 style={{ fontSize: 'clamp(26px, 4vw, 40px)', marginBottom: 8 }}>创建一个学习讨论室</h1>
      {/* redirect-02（Q2=2）：房主职责那句解释由名言替换 —— 表单本身与下方按钮承担引导 */}
      <QuoteLine scene="learn" />
      <div className="card">
        <RoomForm
          submitting={createRoom.isPending}
          error={createRoom.error}
          onSubmit={(body) =>
            createRoom.mutate(body, {
              onSuccess: (room) => navigate(`/rooms/${room.id}/live`, { state: { flash: '房间已创建，你是房主' } }),
            })
          }
        />
      </div>
    </div>
  )
}
