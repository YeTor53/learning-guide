/** 管理后台 · 审计流水表（r012）：纯展示。 */
import type { AdminAudit } from '../../api/admin'

interface Props {
  entries: AdminAudit[]
}

const ACTION_LABEL: Record<string, string> = {
  'room.end': '结束房间',
  'room.delete': '删除房间',
  'room.summary_regenerate': '重生纪要',
}

function when(iso: string): string {
  const date = new Date(iso)
  return Number.isNaN(date.getTime())
    ? '—'
    : date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function summaryOf(detail: Record<string, unknown>): string {
  const snapshot = detail.snapshot
  if (snapshot && typeof snapshot === 'object') {
    const title = (snapshot as Record<string, unknown>).title
    if (typeof title === 'string') return title
  }
  const title = detail.title
  return typeof title === 'string' ? title : '—'
}

export default function AdminAuditTable({ entries }: Props) {
  if (entries.length === 0) return <p className="empty dim">还没有管理动作</p>

  return (
    <div className="admin-table-wrap">
      <table className="admin-table">
        <thead>
          <tr>
            <th>时间</th>
            <th>操作人</th>
            <th>动作</th>
            <th>对象</th>
            <th>摘要</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => (
            <tr key={entry.id}>
              <td className="dim">{when(entry.createdAt)}</td>
              <td>{entry.actorName ?? '（已注销）'}</td>
              <td>{ACTION_LABEL[entry.action] ?? entry.action}</td>
              <td className="dim">
                {entry.targetType} · {entry.targetId}
              </td>
              <td className="dim">{summaryOf(entry.detail)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
