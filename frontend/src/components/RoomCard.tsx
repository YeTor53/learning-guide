import { ArrowUpRight, CalendarX2, Clock, Crown, Hash, ShieldCheck, UserRound, Users } from 'lucide-react'
import { useCallback, useRef } from 'react'
import { Link } from 'react-router-dom'

import { ROLE_LABEL, type Room } from '../api/rooms'

const ICON = { size: 13, strokeWidth: 1.75 } as const

const ROLE_ICON = {
  host: <Crown {...ICON} />,
  moderator: <ShieldCheck {...ICON} />,
  participant: <UserRound {...ICON} />,
} as const

function truncate(text: string, limit = 68) {
  return text.length > limit ? `${text.slice(0, limit)}…` : text
}

/**
 * 房间卡：指针跟随聚光 + 轻微倾斜（写 CSS 变量，动效由样式表接管；减少动效时自动降级）。
 */
export default function RoomCard({ room, index = 0 }: { room: Room; index?: number }) {
  const ref = useRef<HTMLElement | null>(null)

  const onPointerMove = useCallback((event: React.PointerEvent<HTMLElement>) => {
    const node = ref.current
    if (!node) return
    const rect = node.getBoundingClientRect()
    const x = (event.clientX - rect.left) / rect.width
    const y = (event.clientY - rect.top) / rect.height
    node.style.setProperty('--mx', `${x * 100}%`)
    node.style.setProperty('--my', `${y * 100}%`)
    node.style.setProperty('--ry', `${(x - 0.5) * 3.2}deg`)
    node.style.setProperty('--rx', `${(0.5 - y) * 3.2}deg`)
  }, [])

  const onPointerLeave = useCallback(() => {
    const node = ref.current
    if (!node) return
    node.style.setProperty('--rx', '0deg')
    node.style.setProperty('--ry', '0deg')
  }, [])

  const filled = room.capacity > 0 ? Math.min(100, Math.round((room.memberCount / room.capacity) * 100)) : 0
  const ended = room.status === 'ended'

  return (
    <article
      ref={ref}
      className="card room-card stagger"
      style={{ ['--i' as string]: index }}
      onPointerMove={onPointerMove}
      onPointerLeave={onPointerLeave}
    >
      <div className="badges" style={{ marginBottom: 12 }}>
        <span className="chip chip-quiet">
          <Hash {...ICON} />
          {room.topicLabel}
        </span>
        {ended ? (
          <span className="chip chip-quiet">
            <CalendarX2 {...ICON} />
            已结束
          </span>
        ) : (
          <span className="chip chip-accent">{room.memberCount > 0 ? '讨论中' : '进行中'}</span>
        )}
        {room.myRole && (
          <span className="chip chip-accent">
            {ROLE_ICON[room.myRole]}
            {ROLE_LABEL[room.myRole]}
          </span>
        )}
        {!room.myRole && room.myRequestStatus === 'pending' && (
          <span className="chip chip-warn">
            <Clock {...ICON} />
            已申请
          </span>
        )}
        {room.pendingCount > 0 && (
          <span className="chip chip-warn">
            <Clock {...ICON} />
            待批 {room.pendingCount}
          </span>
        )}
      </div>

      <Link to={`/rooms/${room.id}`} style={{ display: 'block' }}>
        <h3 style={{ fontSize: 20, display: 'flex', alignItems: 'baseline', gap: 8 }}>
          {room.title}
          <ArrowUpRight size={16} strokeWidth={1.75} style={{ color: 'var(--text-mute)', flex: '0 0 16px' }} />
        </h3>
      </Link>

      {room.description && (
        <p className="muted" style={{ margin: '8px 0 16px', fontSize: 14 }}>
          {truncate(room.description)}
        </p>
      )}

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginTop: 'auto' }}>
        <span className="dim" style={{ fontSize: 12 }}>
          {room.hostName}
        </span>
        <span className="chip chip-quiet">
          <Users {...ICON} />
          {room.memberCount}/{room.capacity}
        </span>
      </div>
      <div className="meter" style={{ marginTop: 12 }} aria-hidden>
        <i style={{ width: `${filled}%` }} />
      </div>
      <span className="mono dim" style={{ fontSize: 11, display: 'block', marginTop: 8 }}>
        {room.roomCode}
      </span>
    </article>
  )
}
