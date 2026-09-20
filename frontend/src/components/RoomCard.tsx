import {History, CalendarX2, Clock, Crown, FileText, Hash, LogIn, Radio, ShieldCheck, UserRound, Users} from 'lucide-react'
import { useCallback, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'

import { ApiError } from '../api/http'
import { ROLE_LABEL, roomsApi, type Room, type ViewerRole } from '../api/rooms'
import { useSession } from '../hooks/useSession'

const ICON = { size: 13, strokeWidth: 1.75 } as const

const ROLE_ICON: Record<ViewerRole, React.ReactNode> = {
  host: <Crown {...ICON} />,
  moderator: <ShieldCheck {...ICON} />,
  participant: <UserRound {...ICON} />,
  superadmin: <ShieldCheck {...ICON} />,
}

function truncate(text: string, limit = 68) {
  return text.length > limit ? `${text.slice(0, limit)}…` : text
}

/**
 * 房间卡：指针跟随聚光 + 轻微倾斜（写 CSS 变量，动效由样式表接管；减少动效时自动降级）。
 *
 * 卡片动作（redirect-06 定稿：房间管理页已删除，列表页是唯一入口）：
 *   - 在册成员 →「回到讨论」（直接进交流页）
 *   - 有待批申请 →「去等待室」
 *   - 未申请 →「申请加入」（提交后直接落等待室，获批自动进入；没有手动"进入房间"这一步）
 *   - 已结束 → 无动作（回看/纪要由 M4 的纪要页承载）
 */
export default function RoomCard({ room, index = 0 }: { room: Room; index?: number }) {
  const ref = useRef<HTMLElement | null>(null)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { user } = useSession()
  const [error, setError] = useState<string | null>(null)

  const join = useMutation({
    mutationFn: () => roomsApi.requestJoin(room.id, ''),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rooms'] })
      navigate(`/rooms/${room.id}/wait`)
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : '申请失败，请稍后重试'),
  })

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
  const full = room.status === 'active' && room.memberCount >= room.capacity
  const pending = !room.myRole && room.myRequestStatus === 'pending'

  const primary = () => {
    // r008：已结束的房间给「讨论纪要」入口（作业必做「结束后可查看纪要」）
    if (ended) {
      // r013：结束后给**回看**入口（历史时间线 + 纪要 + 成员）；原「讨论纪要」按钮保留，
      // 不动 r008 那条验收路径（作业必做「结束后可查看纪要」的证据链指着它）。
      return (
        <>
          <button className="btn btn-primary btn-sm" onClick={() => navigate(`/rooms/${room.id}/replay`)}>
            <History {...ICON} />
            回看
          </button>
          <button className="btn btn-sm" onClick={() => navigate(`/rooms/${room.id}/summary`)}>
            <FileText {...ICON} />
            讨论纪要
          </button>
        </>
      )
    }
    if (room.myRole) {
      return (
        <button className="btn btn-primary btn-sm" onClick={() => navigate(`/rooms/${room.id}/live`)}>
          <Radio {...ICON} />
          回到讨论
        </button>
      )
    }
    if (pending) {
      return (
        <button className="btn btn-sm" onClick={() => navigate(`/rooms/${room.id}/wait`)}>
          <Clock {...ICON} />
          去等待室
        </button>
      )
    }
    // 满员：不给「点了才报错」的按钮 —— 直接禁用并把原因写在按钮上
    // （2026-09-19 追加，用户报满员时「不能申请」的体验不对）
    if (full) {
      return (
        <button
          className="btn btn-sm"
          disabled
          title={`本场名额已满（在册成员 ${room.memberCount}/${room.capacity}，等于上限）`}
        >
          <Users {...ICON} />
          已满
        </button>
      )
    }
    return (
      <button
        className="btn btn-primary btn-sm"
        disabled={join.isPending}
        onClick={() => {
          setError(null)
          if (!user) {
            navigate(`/login?returnTo=${encodeURIComponent('/')}`)
            return
          }
          join.mutate()
        }}
      >
        <LogIn {...ICON} />
        {join.isPending ? '提交中…' : '申请加入'}
      </button>
    )
  }

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
        {!ended && full && (
          <span className="chip chip-warn">
            <Users {...ICON} />
            已满
          </span>
        )}
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
        {pending && (
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

      <h3 style={{ fontSize: 20 }}>{room.title}</h3>

      {room.description && (
        <p className="muted" style={{ margin: '8px 0 16px', fontSize: 14 }}>
          {truncate(room.description)}
        </p>
      )}

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginTop: 'auto' }}>
        <span className="dim" style={{ fontSize: 12 }}>
          {room.hostName}
        </span>
        <span className={`chip ${full ? 'chip-warn' : 'chip-quiet'}`} title={full ? '本场名额已满（在册成员 = 上限）' : '在册成员 / 上限'}>
          <Users {...ICON} />
          {room.memberCount}/{room.capacity}
          {full ? ' 已满' : ''}
        </span>
      </div>

      {error && (
        <p style={{ color: 'var(--danger)', fontSize: 12, margin: '8px 0 0' }}>{error}</p>
      )}

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, marginTop: 12 }}>
        <span className="mono dim" style={{ fontSize: 11 }}>
          {room.roomCode}
        </span>
        {primary()}
      </div>
      <div className="meter" style={{ marginTop: 12 }} aria-hidden>
        <i style={{ width: `${filled}%` }} />
      </div>
    </article>
  )
}
