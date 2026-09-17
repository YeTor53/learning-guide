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
    <div className="card stack" style={{ maxWidth: 420, margin: '0 auto' }}>
      <h2>注册</h2>
      <RegisterForm
        submitting={register.isPending}
        error={register.error}
        onSubmit={(body) =>
          register.mutate(body, {
            onSuccess: () => navigate(returnTo),
          })
        }
      />
      <p className="muted">
        已有账号？<Link to={`/login?returnTo=${encodeURIComponent(returnTo)}`}>去登录</Link>
      </p>
    </div>
  )
}
