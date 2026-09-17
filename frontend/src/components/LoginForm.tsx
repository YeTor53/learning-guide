import { AlertTriangle, Lock, LogIn, Mail } from 'lucide-react'
import { useState } from 'react'

import { ApiError } from '../api/http'

interface Props {
  submitting: boolean
  error: unknown
  onSubmit: (body: { email: string; password: string }) => void
}

const ICON = { size: 14, strokeWidth: 1.75 } as const

/** 登录表单（拦截顺序与文案见功能页 F-A-02）：本地预检只为少一次往返，服务端为准。 */
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
    <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {message && (
        <div className="alert" role="alert">
          <AlertTriangle size={16} strokeWidth={1.75} style={{ marginTop: 2, flex: '0 0 16px' }} />
          {message}
        </div>
      )}
      <div className="field">
        <label htmlFor="login-email">
          <Mail {...ICON} style={{ verticalAlign: -2, marginRight: 6 }} />
          邮箱
        </label>
        <input id="login-email" className="input" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" placeholder="you@example.com" />
      </div>
      <div className="field">
        <label htmlFor="login-password">
          <Lock {...ICON} style={{ verticalAlign: -2, marginRight: 6 }} />
          密码
        </label>
        <input
          id="login-password"
          className="input"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          placeholder="至少 8 位"
        />
      </div>
      <button className="btn btn-primary" type="submit" disabled={submitting}>
        <LogIn {...ICON} size={16} />
        {submitting ? '登录中…' : '登录'}
      </button>
    </form>
  )
}
