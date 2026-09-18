import { AlertTriangle, AtSign, Lock, PenLine, UserPlus } from 'lucide-react'
import { useState } from 'react'

import { ApiError } from '../api/http'

interface Props {
  submitting: boolean
  error: unknown
  onSubmit: (body: { email: string; displayName: string; password: string }) => void
}

const ICON = { size: 14, strokeWidth: 1.75 } as const

/** 注册表单（拦截顺序与文案见功能页 F-A-01）。 */
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
    <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {message && (
        <div className="alert" role="alert">
          <AlertTriangle size={16} strokeWidth={1.75} style={{ marginTop: 2, flex: '0 0 16px' }} />
          {message}
        </div>
      )}
      <div className="field">
        <label htmlFor="register-email">
          <AtSign {...ICON} style={{ verticalAlign: -2, marginRight: 6 }} />
          邮箱
        </label>
        <input id="register-email" className="input" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" placeholder="you@example.com" />
      </div>
      <div className="field">
        <label htmlFor="register-name">
          <PenLine {...ICON} style={{ verticalAlign: -2, marginRight: 6 }} />
          显示名
        </label>
        <input id="register-name" className="input" value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="房间里显示的名字" />
      </div>
      <div className="field">
        <label htmlFor="register-password">
          <Lock {...ICON} style={{ verticalAlign: -2, marginRight: 6 }} />
          密码
        </label>
        <input
          id="register-password"
          className="input"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="new-password"
          placeholder="至少 8 位"
        />
      </div>
      <button className="btn btn-primary" type="submit" disabled={submitting}>
        <UserPlus {...ICON} size={16} />
        {submitting ? '注册中…' : '注册'}
      </button>
    </form>
  )
}
