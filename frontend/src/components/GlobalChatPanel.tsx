/** 全服大屏（r012）**面板本体**：可装在两种壳里（r013 cp-6 拆分）。
 *
 * - `variant="drawer"`：装在 `GlobalChatDrawer` 的右侧抽屉里（常规页顶栏「大屏」开合，行为与 r012 一致）；
 * - `variant="embedded"`：装在**交流页右抽屉**的第四个 tab「大屏」里（r013，你的口径变更）——去掉外投影与固定宽度，
 *   标题行保留 × 收起（交给壳决定显示与否）。
 *
 * 数据源仍是 `useGlobalChat(enabled)`（单例 react-query + SSE 失效 + 30 秒兜底轮询），
 * 因此**同时只会有一种壳在拉数据**：`enabled` 由壳按「抽屉开着 / tab 选中」传入。
 * 未登录只读（输入区禁用 + 去登录）。
 */
import { MessagesSquare, Send, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { GLOBAL_BODY_MAX } from '../api/globalChat'
import { ApiError } from '../api/http'
import { useGlobalChat } from '../hooks/useGlobalChat'
import { useSession } from '../hooks/useSession'

export interface GlobalChatPanelProps {
  /** drawer：右侧抽屉壳；embedded：交流页抽屉里的 tab。 */
  variant?: 'drawer' | 'embedded'
  /** 是否该拉数据与接 SSE（抽屉开着 / tab 选中）。 */
  enabled: boolean
  /** 收起按钮（embedded 时不传则不渲染该按钮）。 */
  onClose?: () => void
}

const ICON = { size: 16, strokeWidth: 1.75 } as const

function timeOf(iso: string): string {
  const date = new Date(iso)
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

export default function GlobalChatPanel({ variant = 'drawer', enabled, onClose }: GlobalChatPanelProps) {
  const { user } = useSession()
  const navigate = useNavigate()
  const { messages, isLoading, isError, error, refetch, send } = useGlobalChat(enabled)
  const [draft, setDraft] = useState('')
  const listRef = useRef<HTMLDivElement | null>(null)
  const apiError = error instanceof ApiError ? error : null

  // 新消息到达后滚到底（只在看面板时滚）
  useEffect(() => {
    if (!enabled) return
    const node = listRef.current
    if (node) node.scrollTop = node.scrollHeight
  }, [enabled, messages.length])

  const onlineCount = messages.filter((item) => item.authorOnline).length
  const canSend = Boolean(user) && draft.trim().length > 0 && !send.isPending

  const submit = () => {
    if (!canSend) return
    send.mutate(draft.trim(), {
      onSuccess: () => setDraft(''),
    })
  }

  return (
    <div className={`gc-panel gc-panel-${variant}`}>
      <div className="gc-drawer-head">
        <span className="gc-title">
          <MessagesSquare {...ICON} />
          大屏
        </span>
        <span className="gc-meta">{onlineCount} 人在线</span>
        {variant === 'drawer' && onClose && (
          <button className="icon-btn" onClick={onClose} title="收起（Esc）" aria-label="收起大屏">
            <X {...ICON} />
          </button>
        )}
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
    </div>
  )
}
