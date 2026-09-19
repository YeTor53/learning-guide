/** 单条消息：自己（右）/ 他人（左）/ 系统（居中灰字）；时间只在间隔 > 5 分钟时显示。
 *
 * 设计事实源：docs/rounds/r004-room-extras/design.md §8.6
 */
import type { Message } from '../../api/rooms'

function clock(iso: string): string {
  const date = new Date(iso)
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

interface Props {
  message: Message
  mine: boolean
  /** 与前一条的间隔是否超过 5 分钟（决定要不要显示时间）。 */
  showTime: boolean
  failed?: boolean
  onRetry?: () => void
}

export default function MessageBubble({ message, mine, showTime, failed = false, onRetry }: Props) {
  if (message.kind === 'system') {
    return <div className="chat-system">{message.body}</div>
  }
  return (
    <div className={`chat-row${mine ? ' chat-row-mine' : ''}`}>
      <div className={`chat-bubble${failed ? ' chat-bubble-failed' : ''}`}>
        {!mine && <span className="chat-who">{message.displayName}</span>}
        <span className="chat-body">{message.body}</span>
        <span className="chat-meta">
          {showTime && <span className="chat-time">{clock(message.createdAt)}</span>}
          {failed && (
            <button className="chat-retry" onClick={onRetry}>
              重发
            </button>
          )}
        </span>
      </div>
    </div>
  )
}
