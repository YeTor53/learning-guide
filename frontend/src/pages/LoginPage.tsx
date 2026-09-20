import { ArrowRight, LogIn } from 'lucide-react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import QuoteLine from '../components/QuoteLine'
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
    <div className="auth-wrap">
      <div>
        <span className="kicker">Welcome back</span>
        <QuoteLine scene="learn" className="auth-quote-line" />
        <p className="dim" style={{ fontSize: 13, marginTop: 16 }}>
          演示账号 host@example.com / demo1234
        </p>
      </div>
      <div className="card">
        <h2 style={{ fontSize: 26, marginBottom: 20 }}>登录</h2>
        <LoginForm
          submitting={login.isPending}
          error={login.error}
          onSubmit={(body) => login.mutate(body, { onSuccess: () => navigate(returnTo) })}
        />
        <p className="dim" style={{ fontSize: 13, marginTop: 16, display: 'flex', alignItems: 'center', gap: 6 }}>
          <LogIn size={14} strokeWidth={1.75} />
          还没有账号？
          <Link to={`/register?returnTo=${encodeURIComponent(returnTo)}`} style={{ color: 'var(--accent)' }}>
            去注册
            <ArrowRight size={13} strokeWidth={1.75} style={{ verticalAlign: -2, marginLeft: 4 }} />
          </Link>
        </p>
      </div>
    </div>
  )
}
