import { Check, Clock, Inbox, X } from 'lucide-react'

import type { JoinRequest } from '../api/rooms'

const ICON = { size: 14, strokeWidth: 1.75 } as const

interface Props {
  requests: JoinRequest[]
  busyId: string | null
  onApprove: (requestId: string) => void
  onReject: (requestId: string) => void
  pendingOnly?: boolean
}

const STATUS_LABEL: Record<JoinRequest['status'], string> = {
  pending: '待批',
  approved: '已批准',
  rejected: '已拒绝',
  withdrawn: '已撤回',
  cancelled: '已取消',
}

export default function JoinRequestList({ requests, busyId, onApprove, onReject, pendingOnly = false }: Props) {
  const visible = pendingOnly ? requests.filter((item) => item.status === 'pending') : requests

  if (visible.length === 0) {
    return (
      <div className="empty" style={{ padding: 'var(--s-5)' }}>
        <span className="icon-ring">
          <Inbox size={20} strokeWidth={1.75} />
        </span>
        <span className="muted" style={{ fontSize: 14 }}>
          暂无待处理申请
        </span>
      </div>
    )
  }

  return (
    <div>
      {visible.map((request) => (
        <div className="req-row" key={request.id}>
          <div style={{ minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 600, fontSize: 14 }}>
              {request.displayName}
              <span className={`chip ${request.status === 'pending' ? 'chip-warn' : 'chip-quiet'}`}>
                {request.status === 'pending' ? <Clock {...ICON} /> : <Check {...ICON} />}
                {STATUS_LABEL[request.status]}
              </span>
            </div>
            {request.message && (
              <p className="muted" style={{ margin: '4px 0 0', fontSize: 14 }}>
                {request.message}
              </p>
            )}
            <span className="dim mono" style={{ fontSize: 11 }}>
              {new Date(request.createdAt).toLocaleString('zh-CN', { hour12: false })}
            </span>
          </div>
          {request.status === 'pending' && (
            <div style={{ display: 'flex', gap: 8, flex: '0 0 auto' }}>
              <button className="btn btn-primary btn-sm" disabled={busyId === request.id} onClick={() => onApprove(request.id)}>
                <Check {...ICON} />
                {busyId === request.id ? '处理中…' : '批准'}
              </button>
              <button className="btn btn-sm btn-danger" disabled={busyId === request.id} onClick={() => onReject(request.id)}>
                <X {...ICON} />
                拒绝
              </button>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
