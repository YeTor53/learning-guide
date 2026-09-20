/** 管理后台 · 纪要表（r012）：纯展示。 */
import type { AdminSummary } from '../../api/admin'

interface Props {
  summaries: AdminSummary[]
}

function when(iso: string): string {
  const date = new Date(iso)
  return Number.isNaN(date.getTime())
    ? '—'
    : date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

export default function AdminSummaryTable({ summaries }: Props) {
  if (summaries.length === 0) return <p className="empty dim">还没有讨论纪要</p>

  return (
    <div className="admin-table-wrap">
      <table className="admin-table">
        <thead>
          <tr>
            <th>房间</th>
            <th>状态</th>
            <th>模型</th>
            <th>字数</th>
            <th>更新时间</th>
          </tr>
        </thead>
        <tbody>
          {summaries.map((item) => (
            <tr key={item.id}>
              <td className="admin-title">{item.roomTitle}</td>
              <td>{item.status === 'ready' ? '已生成' : item.status === 'failed' ? '生成失败' : item.status}</td>
              <td className="dim">{item.model || '—'}</td>
              <td>{item.contentLength}</td>
              <td className="dim">{when(item.updatedAt)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
