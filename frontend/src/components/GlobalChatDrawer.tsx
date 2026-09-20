/** 全服大屏（r012）：右侧可收起侧栏面板（编辑器 Copilot 式，Q11=2）。
 *
 * 交互：右上角开合按钮（顶栏）→ 抽屉从右侧滑入；Esc 收起；未登录只读（输入区禁用 + 去登录）。
 * 样式参数集中在 `global.css` 的 r012 参数区（`--gc-w` 等），组件里不写死尺寸与颜色。
 */
import { MessagesSquare, Send, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { ApiError } from '../api/http'
import { GLOBAL_BODY_MAX } from '../api/globalChat'
import { useGlobalChat } from '../hooks/useGlobalChat'
import { useSession } from '../hooks/useSession'

interface Props {
  open: boolean
  onClose: () => void
}

const ICON = { size: 16, strokeWidth: 1.75 } as const

function timeOf(iso: string): string {
  const date = new Date(iso)
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

export default function GlobalChatDrawer({ open, onClose }: Props) {
  const { user } = useSession()
  const navigate = useNavigate()
  const { messages, isLoading, isError, error, refetch, send } = useGlobalChat(open)
  const [draft, setDraft] = useState('')
  const listRef = useRef<HTMLDivElement | null>(null)
  const apiError = error instanceof ApiError ? error : null

  // Esc 收起（与既有抽屉一致：永远有退路）
  useEffect(() => {
    if (!open) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  // 新消息到达后滚到底（只在不看历史时滚）
  useEffect(() => {
    if (!open) return
    const node = listRef.current
    if (node) node.scrollTop = node.scrollHeight
  }, [open, messages.length])

  const onlineCount = messages.filter((item) => item.authorOnline).length
  const canSend = Boolean(user) && draft.trim().length > 0 && !send.isPending

  const submit = () => {
    if (!canSend) return
    send.mutate(draft.trim(), {
      onSuccess: () => setDraft(''),
    })
  }

  return (
    <aside className={`gc-drawer${open ? ' on' : ''}`} aria-hidden={!open} aria-label="全服大屏聊天">
      <div className="gc-drawer-head">
        <span className="gc-title">
          <MessagesSquare {...ICON} />
          大屏
        </span>
        <span className="gc-meta">{onlineCount} 人在线</span>
        <button className="icon-btn" onClick={onClose} title="收起（Esc）" aria-label="收起大屏">
          <X {...ICON} />
        </button>
      </div>

      <div className="chat-list gc-list" ref={listRef}>
        {isLoading && <p className="chat-empty dim">正在加载…</p>}
        {isError && (
          <div className="chat-error">
            <p>{apiError?.message ?? '大屏暂时不可用'}</p>
            <button className="btn btn-sm" onClick={() => void refetch()}>
              重试
            </button>
          </div>
        )}
        {!isLoading && !isError && messages.length === 0 && <p className="chat-empty dim">还没有人说话，说第一句吧</p>}
        {messages.map((item) => (
          <div key={item.id} className={`chat-row${user && item.userId === user.id ? ' chat-row-mine' : ''}`}>
            <div className="chat-meta">
              <span className="chat-who">{item.displayName}</span>
              {item.authorOnline && <span className="gc-online-dot" title="当前在线" aria-label="当前在线" />}
              <span className="chat-time">{timeOf(item.createdAt)}</span>
            </div>
            <p className="chat-bubble">{item.body}</p>
          </div>
        ))}
      </div>

      <div className="chat-input">
        {user ? (
          <>
            <textarea
              className="chat-textarea"
              value={draft}
              maxLength={GLOBAL_BODY_MAX}
              placeholder="对所有人说一句…"
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault()
                  submit()
                }
              }}
            />
            <div className="chat-input-foot">
              <span className="dim">
                {draft.length} / {GLOBAL_BODY_MAX}
              </span>
              <button className="btn btn-primary btn-sm" onClick={submit} disabled={!canSend}>
                <Send size={14} strokeWidth={1.75} />
                {send.isPending ? '发布中' : '发布'}
              </button>
            </div>
          </>
        ) : (
          <div className="gc-login-hint">
            <p className="dim">登录后可以发言，未登录只能看。</p>
            <button className="btn btn-sm btn-primary" onClick={() => navigate('/login?returnTo=/')}>
              去登录
            </button>
          </div>
        )}
        {send.isError && <p className="chat-error-text">{send.error instanceof ApiError ? send.error.message : '发送失败，请重试'}</p>}
      </div>
    </aside>
  )
}
