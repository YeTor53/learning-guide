import { Calendar, Home, LogIn, LogOut, Mail, PanelLeftClose, PanelLeftOpen, Plus, UserPlus, Users } from 'lucide-react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import { useSession } from '../hooks/useSession'

interface Props {
  collapsed: boolean
  onToggleCollapsed: () => void
}

interface ItemProps {
  to: string
  label: string
  icon: React.ReactNode
  collapsed: boolean
  active: boolean
}

function Item({ to, label, icon, collapsed, active }: ItemProps) {
  return (
    <Link className={`side-item${active ? ' active' : ''}`} to={to} title={label} aria-current={active ? 'page' : undefined}>
      {icon}
      {!collapsed && <span className="label">{label}</span>}
    </Link>
  )
}

const ICON = { size: 18, strokeWidth: 1.75 } as const

/**
 * 左侧边栏：主导航 + 个人信息 + 会话操作（ADR-0007）。
 * 个人信息直接复用 GET /api/auth/me 的 UserVO，不新增页面与接口。
 */
export default function SideBar({ collapsed, onToggleCollapsed }: Props) {
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

  return (
    <aside className={`sidebar${collapsed ? ' collapsed' : ''}`} aria-label="侧边栏">
      <nav className="side-nav">
        {!collapsed && <div className="side-label">导航</div>}
        <Item to="/" label="返回主页" icon={<Home {...ICON} />} collapsed={collapsed} active={isActive('/')} />
        <Item to="/?mine=1" label="我的房间" icon={<Users {...ICON} />} collapsed={collapsed} active={isActive('/?mine=1')} />
        <Item to="/rooms/new" label="创建房间" icon={<Plus {...ICON} />} collapsed={collapsed} active={isActive('/rooms/new')} />
      </nav>

      <section className="side-block">
        {!collapsed && <div className="side-label">个人信息</div>}
        {isLoading ? (
          <span className="dim" style={{ fontSize: 13 }}>{collapsed ? '·' : '加载中…'}</span>
        ) : user ? (
          <>
            <div className="side-user">
              <div className="side-avatar" aria-hidden>
                {user.displayName.slice(0, 1)}
              </div>
              {!collapsed && (
                <div style={{ minWidth: 0 }}>
                  <div className="side-user-name">{user.displayName}</div>
                  <div className="mono dim" style={{ fontSize: 11 }}>
                    {user.id.slice(0, 12)}
                  </div>
                </div>
              )}
            </div>
            {!collapsed && (
              <div className="side-user-line" title={user.email}>
                <Mail size={12} strokeWidth={1.75} style={{ verticalAlign: -1, marginRight: 6 }} />
                {user.email}
              </div>
            )}
            {!collapsed && (
              <div className="side-user-line">
                <Calendar size={12} strokeWidth={1.75} style={{ verticalAlign: -1, marginRight: 6 }} />
                注册于 {new Date(user.createdAt).toLocaleDateString('zh-CN')}
              </div>
            )}
          </>
        ) : (
          !collapsed && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <span className="dim" style={{ fontSize: 12 }}>
                未登录：登录后可建房、申请加入并查看「我的房间」。
              </span>
              <div style={{ display: 'flex', gap: 8 }}>
                <button className="btn btn-primary btn-sm" onClick={() => navigate('/login')}>
                  <LogIn {...ICON} size={15} />
                  登录
                </button>
                <button className="btn btn-sm" onClick={() => navigate('/register')}>
                  <UserPlus {...ICON} size={15} />
                  注册
                </button>
              </div>
            </div>
          )
        )}
      </section>

      <div className="side-foot">
        {user && (
          <button
            className="side-item"
            disabled={logout.isPending}
            onClick={() => logout.mutate(undefined, { onSuccess: () => navigate('/') })}
            title="登出"
          >
            <LogOut {...ICON} />
            {!collapsed && <span className="label">登出</span>}
          </button>
        )}
        <button className="side-item" onClick={onToggleCollapsed} title={collapsed ? '展开侧边栏' : '收起侧边栏'}>
          {collapsed ? <PanelLeftOpen {...ICON} /> : <PanelLeftClose {...ICON} />}
          {!collapsed && <span className="label">收起侧边栏</span>}
        </button>
      </div>
    </aside>
  )
}
