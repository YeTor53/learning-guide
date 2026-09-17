import { Archive, Crown, LogOut, ShieldCheck, UserMinus, UserRound } from 'lucide-react'

import { EXIT_REASON_LABEL, ROLE_LABEL, type ExitReason, type Member } from '../api/rooms'

const ICON = { size: 13, strokeWidth: 1.75 } as const

const ROLE_ICON = {
  host: <Crown {...ICON} />,
  moderator: <ShieldCheck {...ICON} />,
  participant: <UserRound {...ICON} />,
} as const

const EXIT_ICON: Record<ExitReason, React.ReactNode> = {
  self_leave: <LogOut {...ICON} />,
  kicked: <UserMinus {...ICON} />,
  room_ended: <Archive {...ICON} />,
}

export default function MemberList({ members }: { members: Member[] }) {
  if (members.length === 0) return <p className="muted">还没有成员</p>
  return (
    <div className="member-grid">
      {members.map((member, index) => (
        <div className={`member-card stagger${member.status === 'inactive' ? ' inactive' : ''}`} style={{ ['--i' as string]: index }} key={member.id}>
          <div className="side-avatar" aria-hidden>
            {member.displayName.slice(0, 1)}
          </div>
          <div style={{ minWidth: 0, flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 600, fontSize: 14 }}>
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{member.displayName}</span>
              <span className="chip chip-quiet">
                {ROLE_ICON[member.role]}
                {ROLE_LABEL[member.role]}
              </span>
            </div>
            <div className="dim" style={{ fontSize: 12 }}>
              {member.status === 'active'
                ? `加入于 ${new Date(member.joinedAt).toLocaleString('zh-CN', { hour12: false })}`
                : member.exitReason && (
                    <span className="chip chip-quiet" style={{ marginTop: 4 }}>
                      {EXIT_ICON[member.exitReason]}
                      {EXIT_REASON_LABEL[member.exitReason]}
                    </span>
                  )}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
