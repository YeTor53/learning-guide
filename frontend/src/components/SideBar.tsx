import { Home, PanelLeftClose, PanelLeftOpen, Plus, Ticket, UserRound, Users } from 'lucide-react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import QuoteLine from './QuoteLine'
import SidebarUserCard from './SidebarUserCard'
import { useSession } from '../hooks/useSession'

interface Props {
  collapsed: boolean
  onToggleCollapsed: () => void
  /** 窄屏横向条形态下隐藏折叠按钮（见 hooks/useNarrowStrip.ts） */
  hideToggle?: boolean
}

interface ItemProps {
  to: string
  label: string
  icon: React.ReactNode
  collapsed: boolean
  active: boolean
  onNavigate?: (event: React.MouseEvent) => void
}

function Item({ to, label, icon, collapsed, active, onNavigate }: ItemProps) {
  return (
    <Link
      className={`side-item${active ? ' active' : ''}`}
      to={to}
      title={label}
      aria-current={active ? 'page' : undefined}
      onClick={onNavigate}
    >
      {icon}
      {!collapsed && <span className="label">{label}</span>}
    </Link>
  )
}

const ICON = { size: 18, strokeWidth: 1.75 } as const

/**
 * 左侧边栏：上半区是主导航，**左下角是个人信息**（登录 / 注册入口在顶栏右上角，见 ADR-0009）。
 * 个人信息复用 `GET /api/auth/me` 的 UserVO，不新增页面与接口。
 */
export default function SideBar({ collapsed, onToggleCollapsed, hideToggle = false }: Props) {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, isLoading, logout } = useSession()

  const onRoomsPage = location.pathname === '/'
  const mineActive = onRoomsPage && new URLSearchParams(location.search).get('mine') === '1'
  const isActive = (to: string) => {
    if (to === '/') return onRoomsPage && !mineActive
    if (to === '/?mine=1') return mineActive
    return location.pathname === to
  }

  // 「我的房间」需要登录：未登录时先去登录页并带回跳（避免直接打接口拿 401）
  const guardMine = (event: React.MouseEvent) => {
    if (user || isLoading) return
    event.preventDefault()
    navigate(`/login?returnTo=${encodeURIComponent('/?mine=1')}`)
  }

  return (
    <aside className={`sidebar${collapsed ? ' collapsed' : ''}`} aria-label="侧边栏">
      <nav className="side-nav">
        {!collapsed && <div className="side-label">导航</div>}
        <Item to="/" label="返回主页" icon={<Home {...ICON} />} collapsed={collapsed} active={isActive('/')} />
        <Item
          to="/?mine=1"
          label="我的房间"
          icon={<Users {...ICON} />}
          collapsed={collapsed}
          active={isActive('/?mine=1')}
          onNavigate={guardMine}
        />
        {/* r011：通用邀请码入口（你 2026-09-20 拍板放在侧边栏，不放顶栏）。
            未登录也能点 —— `/join` 页自己会把「加入房间」换成「去登录并加入」，登录后自动回到同一个码。 */}
        <Item to="/join" label="邀请码加入" icon={<Ticket {...ICON} />} collapsed={collapsed} active={isActive('/join')} />
        {/* r011：创建房间按你的口径**放最下面**（导航列表最后一项；列表页顶部还有一个同名按钮，两处都会建房） */}
        <Item to="/rooms/new" label="创建房间" icon={<Plus {...ICON} />} collapsed={collapsed} active={isActive('/rooms/new')} />
      </nav>

      <div className="side-spacer" />

      <section className="side-foot">
        {!collapsed && <div className="side-label">个人信息</div>}
        {isLoading ? (
          <span className="dim" style={{ fontSize: 13 }}>
            {collapsed ? '·' : '加载中…'}
          </span>
        ) : user ? (
          <SidebarUserCard
            user={user}
            collapsed={collapsed}
            onExpand={onToggleCollapsed}
            logoutPending={logout.isPending}
            onLogout={() => logout.mutate(undefined, { onSuccess: () => navigate('/') })}
          />
        ) : (
          <div className="side-user">
            {!collapsed ? (
              <>
                <div className="side-avatar" aria-hidden>
                  <UserRound size={16} strokeWidth={1.75} />
                </div>
                <QuoteLine scene="self" className="side-quote" />
              </>
            ) : (
              <div className="side-avatar" aria-hidden>
                <UserRound size={16} strokeWidth={1.75} />
              </div>
            )}
          </div>
        )}

        {!hideToggle && (
          <button className="side-item" onClick={onToggleCollapsed} title={collapsed ? '展开侧边栏' : '收起侧边栏'}>
            {collapsed ? <PanelLeftOpen {...ICON} /> : <PanelLeftClose {...ICON} />}
            {!collapsed && <span className="label">收起侧边栏</span>}
          </button>
        )}
      </section>
    </aside>
  )
}
