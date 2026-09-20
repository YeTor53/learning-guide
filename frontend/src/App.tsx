import { useState } from 'react'
import { Link, Navigate, Route, Routes, useLocation } from 'react-router-dom'

import QuoteLine from './components/QuoteLine'
import NavBar from './components/NavBar'
import SideBar from './components/SideBar'
import useNarrowStrip from './hooks/useNarrowStrip'
import LoginPage from './pages/LoginPage'
import NewRoomPage from './pages/NewRoomPage'
import RegisterPage from './pages/RegisterPage'
import RoomLivePage from './pages/RoomLivePage'
import WaitingPage from './pages/WaitingPage'
import RoomsPage from './pages/RoomsPage'

/** 五条路由（架构页 §9.7 + r002 两页；redirect-06 起删除 `/rooms/:id` 房间管理页）：/ 、/login、/register、/rooms/new、/rooms/:id/live
 *
 * 交流页（`/rooms/:id/live`）**隐藏全局侧边栏与外层容器**——专注感要求（redirect-04 §4.2、FQ-16）。
 */
/** 侧边栏收起状态的存储键（r007）；首次访问无值时按「收起」处理。 */
const SIDEBAR_KEY = 'lg.sidebar.collapsed'

export default function App() {
  // r007：侧边栏**默认收起**（首次访问），用户手动切换后记住选择
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try {
      const saved = localStorage.getItem(SIDEBAR_KEY)
      return saved === null ? true : saved === '1'
    } catch {
      return true
    }
  })
  const location = useLocation()
  const toggle = () => {
    setCollapsed((value) => {
      const next = !value
      try {
        localStorage.setItem(SIDEBAR_KEY, next ? '1' : '0')
      } catch {
        // 隐私模式/存储不可用：忽略，退回「本次会话内生效」
      }
      return next
    })
  }
  // 窄屏（≤900px）侧边栏是顶部横向条：折叠既无意义又会被 React 去掉标签，故强制按展开渲染
  const narrowStrip = useNarrowStrip()

  const isLive = /^\/rooms\/[^/]+\/live$/.test(location.pathname)
  const routes = (
    <Routes>
      <Route path="/" element={<RoomsPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/rooms/new" element={<NewRoomPage />} />
        <Route path="/rooms/:id/live" element={<RoomLivePage />} />
      <Route path="/rooms/:id/wait" element={<WaitingPage />} />
      {/* 旧「房间管理页」链接（分享出去的 /rooms/:id）不再报空页，直接回列表 */}
      <Route path="/rooms/:id" element={<Navigate to="/" replace />} />
      <Route
        path="*"
        element={
          <div className="card" style={{ maxWidth: 420, margin: '48px auto', textAlign: 'center' }}>
            <p style={{ margin: '0 0 4px' }}>页面不存在</p>
            <QuoteLine scene="farewell" />
            <Link className="btn btn-sm" to="/">
              回房间列表
            </Link>
          </div>
        }
      />
    </Routes>
  )

  return (
    <div className="app">
      <NavBar onToggleCollapsed={toggle} />
      {isLive ? (
        <main className="content route-fade" key={location.pathname}>
          {routes}
        </main>
      ) : (
        <div className="layout">
          <SideBar collapsed={collapsed && !narrowStrip} onToggleCollapsed={toggle} hideToggle={narrowStrip} />
          {/* key 变化触发路由级淡入（动效清单见 docs/04-style/global-style.md §6） */}
          <main className="content route-fade" key={`${location.pathname}${location.search}`}>
            <div className="container">{routes}</div>
          </main>
        </div>
      )}
    </div>
  )
}
