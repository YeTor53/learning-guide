/** 管理抽屉（默认收起）：成员 + 待批申请 + 房间信息 + 管理动作。
 *
 * 设计事实源：docs/02-modules/r002-livekit-features.md §4.2（按钮矩阵）、FQ-14（收进抽屉）。
 */
import { ShieldCheck, ShieldOff, UserMinus, Crown } from 'lucide-react'

import JoinRequestList from '../JoinRequestList'
import type { JoinRequest, Member, Room, Role } from '../../api/rooms'
import { EXIT_REASON_LABEL, ROLE_LABEL } from '../../api/rooms'

const ICON = { size: 14, strokeWidth: 1.75 } as const

interface Props {
  room: Room
  members: Member[]
  myRole: Role | null
  onlineIds: string[]
  requests: JoinRequest[]
  busyId: string | null
  onKick: (userId: string) => void
  onSetRole: (userId: string, role: Exclude<Role, 'host'>) => void
  onTransferHost: (userId: string) => void
  onApprove: (requestId: string) => void
  onReject: (requestId: string) => void
}

export default function RoomSidePanel({
  room,
  members,
  myRole,
  onlineIds,
  requests,
  busyId,
  onKick,
  onSetRole,
  onTransferHost,
  onApprove,
  onReject,
}: Props) {
  const isHost = myRole === 'host'
  const isManager = myRole === 'host' || myRole === 'moderator'
  const online = new Set(onlineIds)

  return (
    <aside className="live-drawer">
      <section className="panel">
        <h2 className="panel-title">成员 {members.length} / {room.capacity}</h2>
        {members.map((member) => (
          <div className="member-row" key={member.id}>
            <div style={{ minWidth: 0 }}>
              <div className="member-name">
                {member.displayName}
                <span className={`chip ${member.role === 'host' ? 'chip-warn' : 'chip-quiet'}`}>
                  {ROLE_LABEL[member.role]}
                </span>
              </div>
              <span className="dim mono" style={{ fontSize: 11 }}>
                {online.has(member.userId) ? '在线' : member.status === 'inactive' ? (member.exitReason ? EXIT_REASON_LABEL[member.exitReason] : '已离开') : '离线'}
              </span>
            </div>
            {isManager && member.userId !== room.hostId && (
              <div className="member-actions">
                <button className="icon-btn" title="移出房间" aria-label={`移出 ${member.displayName}`} disabled={busyId === member.userId} onClick={() => onKick(member.userId)}>
                  <UserMinus {...ICON} />
                </button>
                {isHost && (
                  <>
                    <button
                      className="icon-btn"
                      title={member.role === 'moderator' ? '取消协管' : '设为协管'}
                      aria-label={member.role === 'moderator' ? `取消 ${member.displayName} 的协管` : `设为协管 ${member.displayName}`}
                      disabled={busyId === member.userId}
                      onClick={() => onSetRole(member.userId, member.role === 'moderator' ? 'participant' : 'moderator')}
                    >
                      {member.role === 'moderator' ? <ShieldOff {...ICON} /> : <ShieldCheck {...ICON} />}
                    </button>
                    <button className="icon-btn" title="移交房主" aria-label={`移交房主给 ${member.displayName}`} disabled={busyId === member.userId} onClick={() => onTransferHost(member.userId)}>
                      <Crown {...ICON} />
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
        ))}
      </section>

      {isManager && (
        <section className="panel">
          <h2 className="panel-title">待处理申请</h2>
          <JoinRequestList requests={requests} busyId={busyId} onApprove={onApprove} onReject={onReject} pendingOnly />
        </section>
      )}

      <section className="panel">
        <h2 className="panel-title">房间信息</h2>
        <p className="muted" style={{ fontSize: 14, margin: 0 }}>{room.topicLabel}</p>
        {room.description && <p className="muted" style={{ fontSize: 14 }}>{room.description}</p>}
        <p className="dim mono" style={{ fontSize: 12, marginBottom: 0 }}>房间码 {room.roomCode}</p>
      </section>
    </aside>
  )
}
