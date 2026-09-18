import { useState } from 'react'
import { Link, Navigate, Route, Routes, useLocation } from 'react-router-dom'

import NavBar from './components/NavBar'
import SideBar from './components/SideBar'
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
export default function App() {
  const [collapsed, setCollapsed] = useState(false)
  const location = useLocation()
  const toggle = () => setCollapsed((value) => !value)

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
            <p className="muted" style={{ margin: '0 0 14px', fontSize: 13 }}>
              链接可能已经失效（房间管理页已在 r002 移除）
            </p>
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
          <SideBar collapsed={collapsed} onToggleCollapsed={toggle} />
          {/* key 变化触发路由级淡入（动效清单见 docs/04-style/global-style.md §6） */}
          <main className="content route-fade" key={`${location.pathname}${location.search}`}>
            <div className="container">{routes}</div>
          </main>
        </div>
      )}
    </div>
  )
}
