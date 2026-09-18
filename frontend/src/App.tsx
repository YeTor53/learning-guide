import { useState } from 'react'
import { Route, Routes, useLocation } from 'react-router-dom'

import NavBar from './components/NavBar'
import SideBar from './components/SideBar'
import LoginPage from './pages/LoginPage'
import NewRoomPage from './pages/NewRoomPage'
import RegisterPage from './pages/RegisterPage'
import RoomDetailPage from './pages/RoomDetailPage'
import RoomLivePage from './pages/RoomLivePage'
import RoomsPage from './pages/RoomsPage'

/** 六条路由（架构页 §9.7 + r002 交流页）：/ 、/login、/register、/rooms/new、/rooms/:id、/rooms/:id/live
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
      <Route path="/rooms/:id" element={<RoomDetailPage />} />
      <Route path="/rooms/:id/live" element={<RoomLivePage />} />
      <Route path="*" element={<p className="muted">页面不存在</p>} />
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
