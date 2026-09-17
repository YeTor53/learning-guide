import { Link, useNavigate } from 'react-router-dom'

import { useSession } from '../hooks/useSession'

export default function NavBar() {
  const { user, isLoading, logout } = useSession()
  const navigate = useNavigate()

  return (
    <header className="navbar spread">
      <Link className="brand" to="/">
        学习讨论室
      </Link>
      <div className="links">
        <Link to="/">房间列表</Link>
        {user && <Link to="/rooms/new">创建房间</Link>}
        {isLoading ? (
          <span className="muted">…</span>
        ) : user ? (
          <>
            <span className="muted">你好，{user.displayName}</span>
            <button
              onClick={() =>
                logout.mutate(undefined, {
                  onSuccess: () => navigate('/'),
                })
              }
              disabled={logout.isPending}
            >
              登出
            </button>
          </>
        ) : (
          <>
            <Link to="/login">登录</Link>
            <Link to="/register">注册</Link>
          </>
        )}
      </div>
    </header>
  )
}
