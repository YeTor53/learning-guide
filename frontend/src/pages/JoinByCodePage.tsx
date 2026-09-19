/** 凭邀请码加入（r008，`/join?code=XXXX`）。
 *
 * 口径：码有效期最长 1 分钟；有效则**直接成为在册成员**并进入交流页；过期/用尽/满员/乱码原样提示服务端文案。
 */
import { useMutation } from '@tanstack/react-query'
import { ArrowLeft, ArrowRight, KeyRound } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { ApiError } from '../api/http'
import { invitesApi } from '../api/invites'
import { useSession } from '../hooks/useSession'

const ICON = { size: 16, strokeWidth: 1.75 } as const

export default function JoinByCodePage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const { user, isLoading } = useSession()
  const [code, setCode] = useState((params.get('code') ?? '').trim())
  const [error, setError] = useState<string | null>(null)

  const accept = useMutation({
    mutationFn: () => invitesApi.accept(code.trim()),
    onSuccess: (result) => navigate(`/rooms/${result.roomId}/live`),
    onError: (err: unknown) => setError(err instanceof ApiError ? err.message : '加入失败，请稍后重试'),
  })

  return (
    <div className="summary-shell">
      <Link className="btn btn-sm" to="/">
        <ArrowLeft {...ICON} />
        回房间列表
      </Link>

      <div className="card summary-card">
        <span className="kicker">
          <KeyRound {...ICON} />
          邀请码加入
        </span>
        <h2 style={{ fontSize: 24, margin: '6px 0 4px' }}>输入邀请码</h2>
        <p className="muted" style={{ marginTop: 0, fontSize: 13 }}>
          邀请码由房主生成、**最长 1 分钟有效**；有效就直接进房间，不用等候室。
        </p>

        <div className="invite-join">
          <input
            className="input mono"
            value={code}
            onChange={(event) => setCode(event.target.value)}
            placeholder="例如 ab34kd"
            aria-label="邀请码"
            maxLength={12}
          />
          <button
            className="btn btn-primary btn-sm"
            disabled={accept.isPending || code.trim().length === 0 || !user || isLoading}
            onClick={() => {
              setError(null)
              accept.mutate()
            }}
          >
            <ArrowRight {...ICON} />
            {accept.isPending ? '加入中…' : '加入房间'}
          </button>
        </div>

        {!user && !isLoading && (
          <p className="muted" style={{ fontSize: 13 }}>
            需要先登录才能加入房间。
          </p>
        )}
        {error && (
          <p style={{ color: 'var(--danger)', fontSize: 13, marginBottom: 0 }} role="alert">
            {error}
          </p>
        )}
      </div>
    </div>
  )
}
