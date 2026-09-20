/** 管理后台 · 用户表（r012）：纯展示。 */
import type { AdminUser } from '../../api/admin'

interface Props {
  users: AdminUser[]
}

function when(iso: string | null): string {
  if (!iso) return '从未上报'
  const date = new Date(iso)
  return Number.isNaN(date.getTime())
    ? '从未上报'
    : date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

export default function AdminUserTable({ users }: Props) {
  if (users.length === 0) return <p className="empty dim">没有匹配的用户</p>

  return (
    <div className="admin-table-wrap">
      <table className="admin-table">
        <thead>
          <tr>
            <th>显示名</th>
            <th>邮箱</th>
            <th>角色</th>
            <th>最后活跃</th>
            <th>在册房间</th>
            <th>房内发言</th>
            <th>大屏发言</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr key={user.id}>
              <td className="admin-title">{user.displayName}</td>
              <td className="dim">{user.email}</td>
              <td>{user.role === 'superadmin' ? '管理员' : '用户'}</td>
              <td className="dim">{when(user.lastSeenAt)}</td>
              <td>{user.activeRooms}</td>
              <td>{user.messageCount}</td>
              <td>{user.globalMessageCount}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
