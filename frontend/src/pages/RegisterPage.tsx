import { ArrowRight, UserPlus } from 'lucide-react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import RegisterForm from '../components/RegisterForm'
import { useSession } from '../hooks/useSession'
import { safeReturnTo } from './LoginPage'

export default function RegisterPage() {
  const [params] = useSearchParams()
  const returnTo = safeReturnTo(params.get('returnTo'))
  const navigate = useNavigate()
  const { register } = useSession()

  return (
    <div className="auth-wrap">
      <div>
        <span className="kicker">New account</span>
        <p className="auth-quote">
          「先有一个名字，<br />
          再有一个可以坐下来的房间。」
        </p>
        <p className="dim" style={{ fontSize: 13, marginTop: 16 }}>
          注册成功即登录，直接回到你要去的地方。
        </p>
      </div>
      <div className="card">
        <h2 style={{ fontSize: 26, marginBottom: 20 }}>注册</h2>
        <RegisterForm
          submitting={register.isPending}
          error={register.error}
          onSubmit={(body) => register.mutate(body, { onSuccess: () => navigate(returnTo) })}
        />
        <p className="dim" style={{ fontSize: 13, marginTop: 16, display: 'flex', alignItems: 'center', gap: 6 }}>
          <UserPlus size={14} strokeWidth={1.75} />
          已有账号？
          <Link to={`/login?returnTo=${encodeURIComponent(returnTo)}`} style={{ color: 'var(--accent)' }}>
            去登录
            <ArrowRight size={13} strokeWidth={1.75} style={{ verticalAlign: -2, marginLeft: 4 }} />
          </Link>
        </p>
      </div>
    </div>
  )
}
