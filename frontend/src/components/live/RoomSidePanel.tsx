/** 管理抽屉（默认收起）：成员 + 待批申请 + 房间信息 + 管理动作。
 *
 * 设计事实源：docs/02-modules/r002-livekit-features.md §3 F-16、§4.2（按钮矩阵）、§4.6（按钮设计决策表）、FQ-14。
 * 按钮原则（r002 定稿）：
 * - 可逆的、常用的 → 文字按钮直接给（移出 / 设为协管 / 取消协管）；
 * - 不可逆且影响全房的（移交房主）→ 收进「更多」菜单，不与其他按钮并排；
 * - 每个动作都有中文文字（不裸图标），危险动作由父组件收口做二次确认。
 */
import { useState } from 'react'
import { Check, Copy, MoreHorizontal, ShieldCheck, ShieldOff, UserMinus, X } from 'lucide-react'

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
  onClose: () => void
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
  onClose,
  onKick,
  onSetRole,
  onTransferHost,
  onApprove,
  onReject,
}: Props) {
  const isHost = myRole === 'host'
  const isManager = myRole === 'host' || myRole === 'moderator'
  const online = new Set(onlineIds)
  const [openMenuId, setOpenMenuId] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const copyCode = async () => {
    try {
      await navigator.clipboard.writeText(room.roomCode)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopied(false)
    }
  }

  return (
    <aside className="live-drawer">
      <div className="live-drawer-head">
        <span className="panel-title" style={{ margin: 0 }}>成员与管理</span>
        <button className="icon-btn" onClick={onClose} title="收起（Esc）" aria-label="收起成员与管理">
          <X {...ICON} />
        </button>
      </div>

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
                {online.has(member.userId)
                  ? '在线'
                  : member.status === 'inactive'
                    ? member.exitReason
                      ? EXIT_REASON_LABEL[member.exitReason]
                      : '已离开'
                    : '离线'}
              </span>
            </div>
            {isManager && member.userId !== room.hostId && (
              <div className="member-actions">
                <button
                  className="btn btn-ghost btn-sm"
                  disabled={busyId === member.userId}
                  onClick={() => onKick(member.userId)}
                  title={`把 ${member.displayName} 移出房间`}
                >
                  <UserMinus {...ICON} />
                  移出
                </button>
                {isHost && (
                  <button
                    className="btn btn-ghost btn-sm"
                    disabled={busyId === member.userId}
                    onClick={() => onSetRole(member.userId, member.role === 'moderator' ? 'participant' : 'moderator')}
                    title={member.role === 'moderator' ? `取消 ${member.displayName} 的协管` : `把 ${member.displayName} 设为协管`}
                  >
                    {member.role === 'moderator' ? <ShieldOff {...ICON} /> : <ShieldCheck {...ICON} />}
                    {member.role === 'moderator' ? '取消协管' : '设为协管'}
                  </button>
                )}
                {isHost && (
                  <div className="more-menu">
                    <button
                      className="icon-btn"
                      aria-haspopup="menu"
                      aria-expanded={openMenuId === member.userId}
                      title="更多"
                      onClick={() => setOpenMenuId(openMenuId === member.userId ? null : member.userId)}
                    >
                      <MoreHorizontal {...ICON} />
                    </button>
                    {openMenuId === member.userId && (
                      <div className="more-menu-pop" role="menu">
                        <button
                          role="menuitem"
                          onClick={() => {
                            setOpenMenuId(null)
                            onTransferHost(member.userId)
                          }}
                        >
                          移交房主给 {member.displayName}
                        </button>
                      </div>
                    )}
                  </div>
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
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="dim mono" style={{ fontSize: 12 }}>房间码 {room.roomCode}</span>
          <button className="btn btn-ghost btn-sm" onClick={() => void copyCode()} title="复制房间码">
            {copied ? <Check {...ICON} /> : <Copy {...ICON} />}
            {copied ? '已复制' : '复制'}
          </button>
        </div>
      </section>
    </aside>
  )
}
