import { Menu, UserRound } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'

import { useSession } from '../hooks/useSession'

interface Props {
  onToggleCollapsed: () => void
}

const CRUMBS: { test: (path: string) => boolean; label: string }[] = [
  { test: (path) => path === '/', label: '房间列表' },
  { test: (path) => path.startsWith('/rooms/new'), label: '创建房间' },
  { test: (path) => path.startsWith('/rooms/'), label: '房间详情' },
  { test: (path) => path.startsWith('/login'), label: '登录' },
  { test: (path) => path.startsWith('/register'), label: '注册' },
]

/** 顶栏：折叠开关 + 品牌 + 当前区块；导航与个人信息都在侧边栏（ADR-0007）。 */
export default function NavBar({ onToggleCollapsed }: Props) {
  const location = useLocation()
  const { user } = useSession()
  const crumb = CRUMBS.find((item) => item.test(location.pathname))?.label ?? '页面'

  return (
    <header className="topbar">
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
        <button className="btn btn-ghost btn-icon" onClick={onToggleCollapsed} title="展开 / 收起侧边栏" aria-label="切换侧边栏">
          <Menu size={18} strokeWidth={1.75} />
        </button>
        <Link className="brand" to="/">
          学习讨论室
        </Link>
        <span className="crumb">
          <span className="sep">/</span>
          {crumb}
          {user && (
            <>
              <span className="sep">/</span>
              <span style={{ color: 'var(--text-dim)' }}>{user.displayName}</span>
            </>
          )}
        </span>
      </div>
      <span className="chip chip-quiet" title="作业题目 A：LiveKit 迷你产品">
        <UserRound size={13} strokeWidth={1.75} />
        题目 A
      </span>
    </header>
  )
}
