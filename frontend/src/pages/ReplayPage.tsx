/** r013 回看页（只读）：房间结束后的**历史入口**。
 *
 * 背景：`ended` 房间原先列表里只有徽标、没有任何入口（原入口随 redirect-06 删管理页一起没了，
 * `docs/00-project/global-roadmap.md` §9 登记为能力缺口）。本页补齐：时间线（聊天+系统消息+转写）/
 * 纪要 / 成员三段，全部只读，**不提供任何写入入口**（房间已结束，讨论不可进）。
 *
 * 事实源：`docs/rounds/r013-demo-readiness/design.md` §4；权限口径见 `useReplay` 注释。
 */
import { ArrowLeft, CalendarClock, FileText, History, Users } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'

import { EXIT_REASON_LABEL, ROLE_LABEL } from '../api/rooms'
import { useReplay } from '../hooks/useReplay'

const ICON = { size: 16, strokeWidth: 1.75 } as const

const KIND_LABEL: Record<string, string> = { chat: '聊天', system: '系统', speech: '转写' }

function when(iso: string | null | undefined): string {
  if (!iso) return '—'
  const date = new Date(iso)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString()
}

export default function ReplayPage() {
  const { id = '' } = useParams()
  const { room, members, timeline, summary, loading, forbidden, errors } = useReplay(id, Boolean(id))

  const active = members.filter((m) => m.status === 'active')
  const left = members.filter((m) => m.status !== 'active')

  return (
    <div className="summary-shell">
      <Link className="btn btn-sm" to="/">
        <ArrowLeft {...ICON} />
        回房间列表
      </Link>

      <div className="card summary-card">
        <span className="kicker">
          <History {...ICON} />
          回看（只读）
        </span>
        <h2 style={{ fontSize: 24, margin: '6px 0 4px' }}>{room?.title ?? (loading ? '加载中…' : '房间')}</h2>
        <p className="muted" style={{ margin: 0, fontSize: 13 }}>
          {room
            ? `${room.topicLabel} · 房主 ${room.hostName} · ${room.status === 'ended' ? '已结束' : '进行中'} · 在册 ${room.memberCount}/${room.capacity} 人`
            : errors.room ?? '加载中…'}
        </p>
        {room && (
          <p className="dim" style={{ margin: '6px 0 0', fontSize: 12 }}>
            <CalendarClock {...ICON} style={{ verticalAlign: '-3px', marginRight: 4 }} />
            结束于 {when(room.endedAt)} · 房间码 {room.roomCode}
          </p>
        )}
        {forbidden && (
          <div className="alert" role="alert" style={{ marginTop: 12 }}>
            这间房的历史只对当时在册的成员与管理身份开放；你的账号不在名单里。
          </div>
        )}
      </div>

      <div className="card">
        <span className="kicker">
          <FileText {...ICON} />
          讨论时间线（聊天 / 系统消息 / 转写）
        </span>
        {errors.timeline && <p className="muted" style={{ fontSize: 13 }}>{errors.timeline}</p>}
        {!errors.timeline && !forbidden && timeline.length === 0 && (
          <p className="muted" style={{ fontSize: 13 }}>{loading ? '加载中…' : '这间房没有留下文字记录。'}</p>
        )}
        {!forbidden && timeline.length > 0 && (
          <ol className="replay-timeline">
            {timeline.map((item) => (
              <li key={item.id} className={`replay-row replay-${item.kind}`}>
                <span className="dim replay-time">{when(item.at)}</span>
                <span className="chip chip-quiet">{KIND_LABEL[item.kind] ?? item.kind}</span>
                <span className="replay-speaker">{item.speakerName ?? '—'}</span>
                <span className="replay-text">{item.text}</span>
              </li>
            ))}
          </ol>
        )}
      </div>

      <div className="card">
        <span className="kicker">
          <FileText {...ICON} />
          讨论纪要
        </span>
        {errors.summary && <p className="muted" style={{ fontSize: 13 }}>{errors.summary}</p>}
        {!errors.summary && !forbidden && !summary && (
          <p className="muted" style={{ fontSize: 13 }}>这间房没有生成纪要。</p>
        )}
        {!forbidden && summary && (
          <>
            <p className="dim" style={{ fontSize: 12, marginTop: 0 }}>
              更新于 {when(summary.updatedAt)} · 模型 {summary.model || '未配置'}
            </p>
            <div className="summary-body" style={{ whiteSpace: 'pre-wrap' }}>{summary.content}</div>
          </>
        )}
        {!forbidden && (
          <p className="dim" style={{ fontSize: 12, marginBottom: 0 }}>
            需要重新生成纪要请到房间列表点该房的「讨论纪要」（房主/协管可操作）。
          </p>
        )}
      </div>

      <div className="card">
        <span className="kicker">
          <Users {...ICON} />
          成员（在册 {active.length} · 曾参与 {left.length}）
        </span>
        <ul className="replay-members">
          {members.map((member) => (
            <li key={member.userId} className="replay-row">
              <span className="replay-speaker">{member.displayName}</span>
              <span className="chip chip-quiet">{ROLE_LABEL[member.role] ?? member.role}</span>
              <span className="dim">
                {member.status === 'active'
                  ? '结束时仍在册'
                  : `已离开${member.exitReason ? `（${EXIT_REASON_LABEL[member.exitReason] ?? member.exitReason}）` : ''}`}
              </span>
            </li>
          ))}
          {members.length === 0 && <li className="muted">没有成员记录。</li>}
        </ul>
      </div>
    </div>
  )
}
