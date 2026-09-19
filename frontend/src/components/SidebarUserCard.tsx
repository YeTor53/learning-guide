/** 侧边栏底部：个人信息的**紧凑入口 + 点击 / focus 才展开的浮窗**（r006，ADR-0017 D3）。
 *
 * 口径：
 * - 默认只留一行（头像 + 名字），不再直接铺开邮箱 / id / 注册日期；
 * - 点击或键盘 focus 打开浮窗（`aria-haspopup="dialog"` / `aria-expanded`）；`Esc` 或点击外部关闭；
 * - 浮窗内容 = 身份信息（名字 / 邮箱 / 加入日期）+ **一句哲学语句（带作者，按日固定）** + 登出；
 * - 收起态（`collapsed`）只显示头像，浮窗不展开（侧边栏太窄放不下）。
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import { ChevronUp, LogOut } from 'lucide-react'

import type { User } from '../api/auth'
import { pickDailyQuote } from '../data/philosophy'

interface Props {
  user: User
  collapsed: boolean
  logoutPending: boolean
  onLogout: () => void
}

const ICON = { size: 18, strokeWidth: 1.75 } as const

export default function SidebarUserCard({ user, collapsed, logoutPending, onLogout }: Props) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement | null>(null)
  const quote = useMemo(() => pickDailyQuote(), [])

  useEffect(() => {
    if (!open) return
    const onPointerDown = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false)
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('pointerdown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('pointerdown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  return (
    <div className="side-user-card" ref={rootRef}>
      <button
        type="button"
        className="side-user-btn"
        aria-haspopup="dialog"
        aria-expanded={open}
        title={`${user.displayName} · ${user.email}`}
        onClick={() => setOpen((value) => !value)}
        onFocus={(event) => {
          // 鼠标点击也会触发 focus；只在「键盘 focus」（`:focus-visible`）时顺势展开，
          // 否则 onFocus 打开、onClick 立刻取反 → 点了反而打不开（cp-3 实测踩到）。
          if (event.currentTarget.matches(':focus-visible')) setOpen(true)
        }}
      >
        <span className="side-avatar" aria-hidden>
          {user.displayName.slice(0, 1)}
        </span>
        {!collapsed && (
          <>
            <span className="side-user-name">{user.displayName}</span>
            <ChevronUp size={14} strokeWidth={1.75} className={`side-user-caret${open ? ' on' : ''}`} />
          </>
        )}
      </button>

      {open && !collapsed && (
        <div className="side-pop" role="dialog" aria-label="个人信息">
          <div className="side-pop-head">
            <span className="side-avatar" aria-hidden>
              {user.displayName.slice(0, 1)}
            </span>
            <div style={{ minWidth: 0 }}>
              <div className="side-user-name">{user.displayName}</div>
              <div className="mono dim" style={{ fontSize: 11 }}>
                {user.email}
              </div>
            </div>
          </div>

          <blockquote className="side-pop-quote">
            {quote.text}
            <cite>—— {quote.author}</cite>
          </blockquote>

          <div className="side-pop-meta">
            加入于 {new Date(user.createdAt).toLocaleDateString('zh-CN')}
          </div>

          <button className="side-item side-pop-logout" disabled={logoutPending} onClick={onLogout} title="登出">
            <LogOut {...ICON} />
            <span className="label">{logoutPending ? '登出中…' : '登出'}</span>
          </button>
        </div>
      )}
    </div>
  )
}
