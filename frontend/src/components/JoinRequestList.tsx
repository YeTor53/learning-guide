import type { JoinRequest } from '../api/rooms'

interface Props {
  requests: JoinRequest[]
  busyId: string | null
  onApprove: (requestId: string) => void
  onReject: (requestId: string) => void
  pendingOnly?: boolean
}

export default function JoinRequestList({ requests, busyId, onApprove, onReject, pendingOnly = false }: Props) {
  const visible = pendingOnly ? requests.filter((item) => item.status === 'pending') : requests
  if (visible.length === 0) return <p className="muted">暂无待处理申请</p>
  return (
    <div className="requests">
      {visible.map((request) => (
        <div className="request" key={request.id}>
          <div>
            <div>
              {request.displayName} <span className="badge">{request.status === 'pending' ? '待批' : request.status}</span>
            </div>
            {request.message && <div className="muted">{request.message}</div>}
            <div className="muted">提交于 {new Date(request.createdAt).toLocaleString('zh-CN', { hour12: false })}</div>
          </div>
          {request.status === 'pending' && (
            <div className="row">
              <button className="primary" disabled={busyId === request.id} onClick={() => onApprove(request.id)}>
                {busyId === request.id ? '处理中…' : '批准'}
              </button>
              <button disabled={busyId === request.id} onClick={() => onReject(request.id)}>
                拒绝
              </button>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
