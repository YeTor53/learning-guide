/** 讨论区（抽屉「讨论」tab）：消息列表 + 输入区。
 *
 * 设计事实源：docs/rounds/r004-room-extras/design.md §8.6（样式）、§5.5（状态来自 useChatMessages）
 * 口径：Enter 发送 / Shift+Enter 换行 / 上限 500 字；失败留在列表里可重发（不吞输入）；新消息 120ms 淡入。
 */
import { useEffect, useMemo, useRef, useState } from 'react'

import { MESSAGE_LIMIT } from '../../api/roomExtras'
import type { Message } from '../../api/rooms'
import type { ChatState } from '../../hooks/useChatMessages'
import MessageBubble from './MessageBubble'

const MAX_LEN = 500
const TIME_GAP_MS = 5 * 60 * 1000

interface Props {
  chat: ChatState
  myUserId: string | null
  /** 未读计数由父组件维护（抽屉收起时也显示徽标）。 */
  onChanged: () => void
}

export default function ChatPanel({ chat, myUserId, onChanged }: Props) {
  const [draft, setDraft] = useState('')
  const listRef = useRef<HTMLDivElement | null>(null)
  const bottomRef = useRef<HTMLDivElement | null>(null)

  const rows = useMemo(() => {
    const all: Message[] = [...chat.messages, ...chat.pending.map((item) => ({
      id: item.id,
      userId: myUserId ?? 'me',
      displayName: '你',
      body: item.body,
      kind: 'chat',
      createdAt: item.createdAt,
    }))]
    return all
      .slice()
      .sort((a, b) => a.createdAt.localeCompare(b.createdAt))
      .map((message, index, list) => ({
        message,
        showTime:
          index === 0 || new Date(message.createdAt).getTime() - new Date(list[index - 1].createdAt).getTime() > TIME_GAP_MS,
      }))
  }, [chat.messages, chat.pending, myUserId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: 'end' })
    onChanged()
  }, [rows.length, onChanged])

  const failedIds = new Set(chat.pending.filter((item) => item.failed).map((item) => item.id))

  const submit = async () => {
    const text = draft.trim()
    if (!text || text.length > MAX_LEN) return
    setDraft('')
    await chat.send(text)
  }

  return (
    <div className="chat-panel">
      <div className="chat-list" ref={listRef}>
        {chat.hasMore && (
          <button className="btn btn-ghost btn-sm chat-more" onClick={() => void chat.loadMore()} disabled={chat.loading}>
            加载更早的消息
          </button>
        )}
        {rows.length === 0 && <p className="chat-empty">还没有人发言</p>}
        {rows.map((row) => (
          <MessageBubble
            key={row.message.id}
            message={row.message}
            mine={row.message.userId === myUserId}
            showTime={row.showTime}
            failed={failedIds.has(row.message.id)}
            onRetry={() => void chat.retry(row.message.id)}
          />
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input">
        <textarea
          className="chat-textarea"
          value={draft}
          maxLength={MAX_LEN}
          placeholder="回车发送 · Shift+回车换行"
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              void submit()
            }
          }}
        />
        <div className="chat-input-foot">
          <span className={`chat-count${draft.length > MAX_LEN - 20 ? ' chat-count-near' : ''}`}>
            {draft.length}/{MAX_LEN}
          </span>
          <button className="btn btn-primary btn-sm" onClick={() => void submit()} disabled={!draft.trim()}>
            发送
          </button>
        </div>
      </div>
      {chat.error && <p className="chat-error">{chat.error}</p>}
      <p className="chat-hint">更早的消息可按「加载更早的消息」翻页（每页 {MESSAGE_LIMIT} 条）</p>
    </div>
  )
}
