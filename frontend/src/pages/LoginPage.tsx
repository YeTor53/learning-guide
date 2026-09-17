import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import LoginForm from '../components/LoginForm'
import { useSession } from '../hooks/useSession'

/** 站内相对路径才允许回跳（功能页 F-A-05：外部地址一律忽略）。 */
export function safeReturnTo(value: string | null): string {
  if (!value || !value.startsWith('/') || value.startsWith('//')) return '/'
  return value
}

export default function LoginPage() {
  const [params] = useSearchParams()
  const returnTo = safeReturnTo(params.get('returnTo'))
  const navigate = useNavigate()
  const { login } = useSession()

  return (
    <div className="card stack" style={{ maxWidth: 420, margin: '0 auto' }}>
      <h2>登录</h2>
      <LoginForm
        submitting={login.isPending}
        error={login.error}
        onSubmit={(body) =>
          login.mutate(body, {
            onSuccess: () => navigate(returnTo),
          })
        }
      />
      <p className="muted">
        还没有账号？<Link to={`/register?returnTo=${encodeURIComponent(returnTo)}`}>去注册</Link>
      </p>
      <p className="muted">演示账号：host@example.com / demo1234</p>
    </div>
  )
}
