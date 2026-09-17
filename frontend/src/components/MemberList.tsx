import { EXIT_REASON_LABEL, ROLE_LABEL, type Member } from '../api/rooms'

function formatTime(value: string) {
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

export default function MemberList({ members }: { members: Member[] }) {
  if (members.length === 0) return <p className="muted">还没有成员</p>
  return (
    <div className="members">
      {members.map((member) => (
        <div className="member" key={member.id}>
          <span>
            {member.displayName} <span className="badge">{ROLE_LABEL[member.role]}</span>
            {member.status === 'inactive' && member.exitReason && (
              <span className="badge ended">{EXIT_REASON_LABEL[member.exitReason]}</span>
            )}
          </span>
          <span className="muted">
            {member.status === 'active' ? `加入于 ${formatTime(member.joinedAt)}` : `离开于 ${formatTime(member.leftAt ?? member.joinedAt)}`}
          </span>
        </div>
      ))}
    </div>
  )
}
