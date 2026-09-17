import { Link } from 'react-router-dom'

import { ROLE_LABEL, type Room } from '../api/rooms'

function truncate(text: string, limit = 60) {
  return text.length > limit ? `${text.slice(0, limit)}…` : text
}

export default function RoomCard({ room }: { room: Room }) {
  const statusText = room.status === 'ended' ? '已结束' : room.memberCount > 0 ? '讨论中' : '进行中'
  return (
    <article className="card stack">
      <div className="row">
        <span className="badge">{room.topicLabel}</span>
        <span className={`badge ${room.status === 'ended' ? 'ended' : 'active'}`}>{statusText}</span>
        {room.myRole && <span className="badge me">我的角色：{ROLE_LABEL[room.myRole]}</span>}
        {!room.myRole && room.myRequestStatus === 'pending' && <span className="badge me">已申请</span>}
        {room.pendingCount > 0 && <span className="badge">待批 {room.pendingCount}</span>}
      </div>
      <div>
        <h3 style={{ margin: 0 }}>
          <Link to={`/rooms/${room.id}`}>{room.title}</Link>
        </h3>
        {room.description && <p className="muted" style={{ margin: '4px 0 0' }}>{truncate(room.description)}</p>}
      </div>
      <div className="spread muted">
        <span>房主 {room.hostName}</span>
        <span>
          成员 {room.memberCount}/{room.capacity}
        </span>
      </div>
    </article>
  )
}
