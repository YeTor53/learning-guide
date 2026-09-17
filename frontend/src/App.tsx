import { Route, Routes } from 'react-router-dom'

import NavBar from './components/NavBar'
import LoginPage from './pages/LoginPage'
import NewRoomPage from './pages/NewRoomPage'
import RegisterPage from './pages/RegisterPage'
import RoomDetailPage from './pages/RoomDetailPage'
import RoomsPage from './pages/RoomsPage'

/** 五条路由（架构页 §9.7）：/ 、/login、/register、/rooms/new、/rooms/:id */
export default function App() {
  return (
    <div className="app">
      <NavBar />
      <main className="container">
        <Routes>
          <Route path="/" element={<RoomsPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/rooms/new" element={<NewRoomPage />} />
          <Route path="/rooms/:id" element={<RoomDetailPage />} />
          <Route path="*" element={<p className="muted">页面不存在</p>} />
        </Routes>
      </main>
    </div>
  )
}
