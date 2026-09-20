/** 房内「邀请」面板（r008）：生成限时邀请码 + 复制链接 + 到期倒计时。
 *
 * 口径（用户 2026-09-19）：有效期**最长 1 分钟**（默认 60 秒），默认 1 次可用；码复制成 `/join?code=XXXX`。
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Copy, Link2, Timer } from 'lucide-react'
import { useEffect, useState } from 'react'

import { ApiError } from '../../api/http'
import { invitesApi, type Invite } from '../../api/invites'

const ICON = { size: 14, strokeWidth: 1.75 } as const

export default function InvitePanel({ roomId }: { roomId: string }) {
  const queryClient = useQueryClient()
  const [ttl, setTtl] = useState(60)
  const [maxUses, setMaxUses] = useState(1)
  const [copied, setCopied] = useState<string | null>(null)
  const [now, setNow] = useState(() => Date.now())

  // 倒计时：每秒推进一次（只影响显示，不请求）
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [])

  const listQuery = useQuery({
    queryKey: ['room-invites', roomId],
    queryFn: () => invitesApi.list(roomId),
    enabled: Boolean(roomId),
  })

  const create = useMutation({
    mutationFn: () => invitesApi.create(roomId, ttl, maxUses),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['room-invites', roomId] }),
  })

  const copy = async (invite: Invite) => {
    const link = `${window.location.origin}/join?code=${invite.code}`
    try {
      await navigator.clipboard.writeText(link)
      setCopied(invite.id)
      window.setTimeout(() => setCopied(null), 1800)
    } catch {
      setCopied(null)
    }
  }

  const invites = listQuery.data?.invites ?? []
  const error = create.error

  return (
    <section className="panel">
      <h2 className="panel-title">邀请链接（限时）</h2>
      <p className="muted" style={{ fontSize: 12, marginTop: 0 }}>
        有效期最长 1 分钟：适合「现在就来」的场景；对方点开链接直接进房，不用等候室。
      </p>

      <div className="invite-form">
        <label className="invite-field">
          <span>有效期</span>
          <select value={ttl} onChange={(event) => setTtl(Number(event.target.value))}>
            <option value={30}>30 秒</option>
            <option value={60}>60 秒</option>
          </select>
        </label>
        <label className="invite-field">
          <span>可用次数</span>
          <select value={maxUses} onChange={(event) => setMaxUses(Number(event.target.value))}>
            {[1, 2, 3, 5].map((n) => (
              <option key={n} value={n}>
                {n} 次
              </option>
            ))}
          </select>
        </label>
        <button className="btn btn-primary btn-sm" onClick={() => create.mutate()} disabled={create.isPending}>
          <Link2 {...ICON} />
          {create.isPending ? '生成中…' : '生成邀请码'}
        </button>
      </div>

      {error && (
        <p style={{ color: 'var(--danger)', fontSize: 12 }}>
          {error instanceof ApiError ? error.message : '生成失败，请稍后重试'}
        </p>
      )}

      {invites.length === 0 && <p className="muted" style={{ fontSize: 13 }}>还没有生成过邀请码。</p>}

      {invites.map((invite) => {
        const left = Math.max(0, Math.round((new Date(invite.expiresAt).getTime() - now) / 1000))
        const dead = invite.expired || left <= 0 || invite.usedCount >= invite.maxUses
        return (
          <div key={invite.id} className={`invite-row${dead ? ' dead' : ''}`}>
            <span className="invite-code mono">{invite.code}</span>
            <button className="btn btn-sm" onClick={() => void copy(invite)}>
              {copied === invite.id ? <Check {...ICON} /> : <Copy {...ICON} />}
              {copied === invite.id ? '已复制' : '复制链接'}
            </button>
            <span className="invite-meta">
              <Timer size={12} strokeWidth={1.75} />
              {dead ? '已失效' : `${left} 秒后过期`} · 已用 {invite.usedCount}/{invite.maxUses}
            </span>
          </div>
        )
      })}
    </section>
  )
}
