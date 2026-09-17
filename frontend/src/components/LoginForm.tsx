import { useState } from 'react'

import { ApiError } from '../api/http'

interface Props {
  submitting: boolean
  error: unknown
  onSubmit: (body: { email: string; password: string }) => void
}

/** 登录表单（文案与拦截顺序见功能页 F-A-02）：前端只做"少一次往返"的检查，服务端为准。 */
export default function LoginForm({ submitting, error, onSubmit }: Props) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [localError, setLocalError] = useState<string | null>(null)

  const submit = (event: React.FormEvent) => {
    event.preventDefault()
    if (!email.trim()) return setLocalError('请输入邮箱')
    if (!password) return setLocalError('请输入密码')
    setLocalError(null)
    onSubmit({ email: email.trim(), password })
  }

  const message = localError ?? (error instanceof ApiError ? error.message : error ? '登录失败，请稍后重试' : null)

  return (
    <form className="stack" onSubmit={submit}>
      {message && <div className="errorbar">{message}</div>}
      <div>
        <label htmlFor="login-email">邮箱</label>
        <input id="login-email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
      </div>
      <div>
        <label htmlFor="login-password">密码</label>
        <input
          id="login-password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
        />
      </div>
      <button className="primary" type="submit" disabled={submitting}>
        {submitting ? '登录中…' : '登录'}
      </button>
    </form>
  )
}
