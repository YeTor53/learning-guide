/** 管理后台 · 房间表（r012）：纯展示 + 动作回调，不含数据获取（便于开发者教学页讲「怎么加一列」）。 */
import { DoorClosed, RefreshCw, Trash2 } from 'lucide-react'

import type { AdminRoom } from '../../api/admin'

interface Props {
  rooms: AdminRoom[]
  busyId: string | null
  confirmId: string | null
  onEnd: (roomId: string) => void
  onDelete: (roomId: string) => void
  onRegenerate: (roomId: string) => void
  onAskConfirm: (roomId: string | null) => void
}

const ICON = { size: 14, strokeWidth: 1.75 } as const

function when(iso: string | null): string {
  if (!iso) return '—'
  const date = new Date(iso)
  return Number.isNaN(date.getTime())
    ? '—'
    : date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

export default function AdminRoomTable({
  rooms,
  busyId,
  confirmId,
  onEnd,
  onDelete,
  onRegenerate,
  onAskConfirm,
}: Props) {
  if (rooms.length === 0) return <p className="empty dim">没有匹配的房间</p>

  return (
    <div className="admin-table-wrap">
      <table className="admin-table">
        <thead>
          <tr>
            <th>房间</th>
            <th>房主</th>
            <th>状态</th>
            <th>在册 / 容量</th>
            <th>待批</th>
            <th>纪要</th>
            <th>创建</th>
            <th>动作</th>
          </tr>
        </thead>
        <tbody>
          {rooms.map((room) => (
            <tr key={room.id}>
              <td>
                <span className="admin-title">{room.title}</span>
                <span className="dim admin-sub">
                  {room.topicLabel} · {room.roomCode}
                </span>
              </td>
              <td>{room.hostName}</td>
              <td>{room.status === 'active' ? '进行中' : '已结束'}</td>
              <td>
                {room.memberCount} / {room.capacity}
              </td>
              <td>{room.pendingCount}</td>
              <td>{room.summaryStatus === 'ready' ? '已生成' : room.summaryStatus === 'failed' ? '生成失败' : '—'}</td>
              <td className="dim">{when(room.createdAt)}</td>
              <td className="admin-actions">
                {room.status === 'active' && (
                  <button className="btn btn-sm" onClick={() => onEnd(room.id)} disabled={busyId === room.id}>
                    <DoorClosed {...ICON} />
                    结束
                  </button>
                )}
                <button className="btn btn-sm" onClick={() => onRegenerate(room.id)} disabled={busyId === room.id}>
                  <RefreshCw {...ICON} />
                  纪要
                </button>
                {confirmId === room.id ? (
                  <span className="admin-confirm">
                    <span className="dim">确认删除？不可恢复</span>
                    <button className="btn btn-sm btn-danger" onClick={() => onDelete(room.id)} disabled={busyId === room.id}>
                      删除
                    </button>
                    <button className="btn btn-sm btn-ghost" onClick={() => onAskConfirm(null)}>
                      取消
                    </button>
                  </span>
                ) : (
                  <button className="btn btn-sm btn-ghost" onClick={() => onAskConfirm(room.id)} disabled={busyId === room.id}>
                    <Trash2 {...ICON} />
                    删除
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
