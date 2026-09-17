import { useState } from 'react'

import { ApiError } from '../api/http'

interface Props {
  submitting: boolean
  error: unknown
  onSubmit: (body: { email: string; displayName: string; password: string }) => void
}

/** 注册表单（文案与拦截顺序见功能页 F-A-01）。 */
export default function RegisterForm({ submitting, error, onSubmit }: Props) {
  const [email, setEmail] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [password, setPassword] = useState('')
  const [localError, setLocalError] = useState<string | null>(null)

  const submit = (event: React.FormEvent) => {
    event.preventDefault()
    if (!email.trim()) return setLocalError('请输入邮箱')
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim())) return setLocalError('邮箱格式不正确')
    if (!displayName.trim()) return setLocalError('请输入显示名')
    if (displayName.trim().length > 32) return setLocalError('显示名最多 32 个字')
    if (password.length < 8) return setLocalError('密码至少 8 位')
    setLocalError(null)
    onSubmit({ email: email.trim(), displayName: displayName.trim(), password })
  }

  const message = localError ?? (error instanceof ApiError ? error.message : error ? '注册失败，请稍后重试' : null)

  return (
    <form className="stack" onSubmit={submit}>
      {message && <div className="errorbar">{message}</div>}
      <div>
        <label htmlFor="register-email">邮箱</label>
        <input id="register-email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
      </div>
      <div>
        <label htmlFor="register-name">显示名</label>
        <input id="register-name" value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
      </div>
      <div>
        <label htmlFor="register-password">密码</label>
        <input
          id="register-password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="new-password"
        />
      </div>
      <button className="primary" type="submit" disabled={submitting}>
        {submitting ? '注册中…' : '注册'}
      </button>
    </form>
  )
}
