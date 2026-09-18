/** 管理抽屉（默认收起）：**活跃 / 非活跃**成员 + 待批申请 + 房间码。
 *
 * 设计事实源：docs/02-modules/r002-livekit-features.md §3 F-16、§4.2（按钮矩阵）、§4.6（按钮决策表）、§4.9（与管理页分工）。
 * 口径（用户 2026-09-18 定）：成员按**在不在房间内**分两类——
 *   - 活跃（在房间里）= 此刻连着房间（LiveKit 在场，ADR-0011 条 1 的"瞬时事实源"）；
 *   - 非活跃（不在房间内）= 此刻不在房间里（离线，或已离开 / 被移出 / 房间结束）。
 * 注意与库里的 `room_members.status` 区分：那是"成员身份是否有效"，不是"此刻在不在"。
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

/** 副行只讲「为什么不在」：仍是成员但离线 → 不写（chip 已经说了不在房间）；已不是成员 → 写原因。 */
function inactiveReason(member: Member): string | null {
  if (member.status !== 'inactive') return null
  return member.exitReason ? `${EXIT_REASON_LABEL[member.exitReason]} · 已不是成员` : '已不是成员'
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

  const activeMembers = members.filter((member) => online.has(member.userId))
  const inactiveMembers = members.filter((member) => !online.has(member.userId))

  const copyCode = async () => {
    try {
      await navigator.clipboard.writeText(room.roomCode)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopied(false)
    }
  }

  const renderRow = (member: Member, active: boolean) => (
    <div className={`member-row${active ? '' : ' member-row-quiet'}`} key={member.id}>
      <div style={{ minWidth: 0 }}>
        <div className="member-name">
          {member.displayName}
          <span className={`chip ${member.role === 'host' ? 'chip-warn' : 'chip-quiet'}`}>{ROLE_LABEL[member.role]}</span>
          <span className={`chip ${active ? 'chip-accent' : 'chip-quiet'}`}>{active ? '在房间里' : '不在房间'}</span>
        </div>
        {!active && inactiveReason(member) && (
          <span className="dim mono" style={{ fontSize: 11 }}>{inactiveReason(member)}</span>
        )}
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
  )

  return (
    <aside className="live-drawer">
      <div className="live-drawer-head">
        <span className="panel-title" style={{ margin: 0 }}>成员与管理</span>
        <button className="icon-btn" onClick={onClose} title="收起（Esc）" aria-label="收起成员与管理">
          <X {...ICON} />
        </button>
      </div>

      <section className="panel">
        <h2 className="panel-title">
          活跃（在房间里）· {activeMembers.length}
          <span className="dim" style={{ fontSize: 12, fontWeight: 400, marginLeft: 8 }}>
            上限 {room.capacity} 人
          </span>
        </h2>
        {activeMembers.length === 0 ? (
          <p className="muted" style={{ fontSize: 13, margin: 0 }}>此刻没有人在房间里</p>
        ) : (
          activeMembers.map((member) => renderRow(member, true))
        )}
      </section>

      <section className="panel">
        <h2 className="panel-title">
          非活跃（不在房间内）· {inactiveMembers.length}
          <span className="dim" style={{ fontSize: 12, fontWeight: 400, marginLeft: 8 }}>
            成员共 {members.length} 人
          </span>
        </h2>
        {inactiveMembers.length === 0 ? (
          <p className="muted" style={{ fontSize: 13, margin: 0 }}>全部成员都在房间里</p>
        ) : (
          inactiveMembers.map((member) => renderRow(member, false))
        )}
      </section>

      {isManager && (
        <section className="panel">
          <h2 className="panel-title">
            待处理申请 · {requests.filter((item) => item.status === 'pending').length}
          </h2>
          <JoinRequestList requests={requests} busyId={busyId} onApprove={onApprove} onReject={onReject} pendingOnly />
        </section>
      )}

      {/* 只留「讨论中要用到」的东西：房间码（口头传播）。主题/简介/时间等归房间管理页（§4.9）。 */}
      <div className="live-code-row">
        <span className="dim mono" style={{ fontSize: 12 }}>房间码 {room.roomCode}</span>
        <button className="btn btn-ghost btn-sm" onClick={() => void copyCode()} title="复制房间码">
          {copied ? <Check {...ICON} /> : <Copy {...ICON} />}
          {copied ? '已复制' : '复制'}
        </button>
      </div>
    </aside>
  )
}
