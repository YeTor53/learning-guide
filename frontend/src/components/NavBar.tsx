import { Menu } from 'lucide-react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import useHideOnScroll from '../hooks/useHideOnScroll'
import { useSession } from '../hooks/useSession'

interface Props {
  onToggleCollapsed: () => void
}

const CRUMBS: { test: (path: string) => boolean; label: string }[] = [
  { test: (path) => path === '/', label: '房间列表' },
  { test: (path) => path.startsWith('/rooms/new'), label: '创建房间' },
  { test: (path) => /^\/rooms\/[^/]+\/live$/.test(path), label: '房间交流' },
  { test: (path) => /^\/rooms\/[^/]+\/wait$/.test(path), label: '房间等待室' },
  { test: (path) => /^\/rooms\/[^/]+\/summary$/.test(path), label: '讨论纪要' },
  { test: (path) => path.startsWith('/join'), label: '邀请码加入' },
  { test: (path) => path.startsWith('/rooms/'), label: '房间' },
  { test: (path) => path.startsWith('/login'), label: '登录' },
  { test: (path) => path.startsWith('/register'), label: '注册' },
]

/**
 * 顶栏：折叠开关 + 品牌 + 当前区块；**右上角是登录 / 注册入口（无边框文字，第一版的位置）**。
 * 个人信息与登出在侧边栏左下角（ADR-0009）。
 */
export default function NavBar({ onToggleCollapsed }: Props) {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, isLoading } = useSession()
  const crumb = CRUMBS.find((item) => item.test(location.pathname))?.label ?? '页面'
  // r007 追加：往下划就隐藏顶栏（向上划 / 回到顶部再回来）
  const hidden = useHideOnScroll()

  return (
    <header className={`topbar${hidden ? ' topbar-hidden' : ''}`}>
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
        </span>
      </div>

      <div className="top-actions">
        {/* r011：常驻入口 —— 作业必做的「邀请」项此前只有房主复制的链接能到，手上有码的人无处输入 */}
        <Link className="link-plain" to="/join">
          邀请码加入
        </Link>
        {isLoading ? (
          <span className="dim" style={{ fontSize: 13 }}>
            ·
          </span>
        ) : user ? (
          <button className="link-plain strong" onClick={() => navigate('/?mine=1')} title="查看我的房间">
            {user.displayName}
          </button>
        ) : (
          <>
            <Link className="link-plain" to="/login">
              登录
            </Link>
            <Link className="link-plain" to="/register">
              注册
            </Link>
          </>
        )}
      </div>
    </header>
  )
}
