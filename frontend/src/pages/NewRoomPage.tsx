import { useNavigate, useSearchParams } from 'react-router-dom'

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

  if (isLoading) return <p className="muted">加载中…</p>
  if (!user) {
    return (
      <div className="card stack" style={{ maxWidth: 460, margin: '0 auto' }}>
        <h2>需要先登录</h2>
        <p className="muted">创建房间需要登录账号。</p>
        <button className="primary" onClick={() => navigate(`/login?returnTo=${encodeURIComponent(returnTo)}`)}>
          去登录
        </button>
      </div>
    )
  }

  return (
    <div className="card stack" style={{ maxWidth: 560, margin: '0 auto' }}>
      <h2>创建房间</h2>
      <RoomForm
        submitting={createRoom.isPending}
        error={createRoom.error}
        onSubmit={(body) =>
          createRoom.mutate(body, {
            onSuccess: (room) => navigate(`/rooms/${room.id}`, { state: { flash: '房间已创建，你是房主' } }),
          })
        }
      />
    </div>
  )
}
