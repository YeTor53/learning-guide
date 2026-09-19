/** 讨论纪要页（r008；作业必做「会后产出」的落地页）。
 *
 * 入口：房间列表里**已结束**的房间卡 →「讨论纪要」。
 * 口径：
 * - 有管理身份（房主/协管）才能生成/重新生成；其他成员只读；
 * - 未配置 LLM 时后端返回 503 `LLM_NOT_CONFIGURED` → 页面给出**明确指引**（不是「失败，请重试」）；
 * - 正文按 markdown 纯文本渲染（`white-space: pre-wrap`，不引入 markdown 依赖）。
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, ArrowLeft, FileText, RefreshCw, Sparkles } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'

import { ApiError } from '../api/http'
import { roomsApi } from '../api/rooms'
import { summaryApi } from '../api/summary'
import { useSession } from '../hooks/useSession'

const ICON = { size: 16, strokeWidth: 1.75 } as const

export default function RoomSummaryPage() {
  const { id = '' } = useParams()
  const queryClient = useQueryClient()
  const { user } = useSession()

  const roomQuery = useQuery({ queryKey: ['live-room', id], queryFn: () => roomsApi.detail(id), enabled: Boolean(id) })
  const summaryQuery = useQuery({ queryKey: ['room-summary', id], queryFn: () => summaryApi.get(id), enabled: Boolean(id) })

  const room = roomQuery.data?.room ?? null
  const myRole = room?.myRole ?? room?.myRoleAny ?? null // 结束后 myRole 为空，用 myRoleAny 兜底（r008）
  const canManage = myRole === 'host' || myRole === 'moderator'

  const generate = useMutation({
    mutationFn: () => summaryApi.generate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['room-summary', id] })
    },
  })

  const error = generate.error
  const notConfigured = error instanceof ApiError && error.code === 'LLM_NOT_CONFIGURED'
  const summary = summaryQuery.data?.summary ?? null

  return (
    <div className="summary-shell">
      <Link className="btn btn-sm" to="/">
        <ArrowLeft {...ICON} />
        回房间列表
      </Link>

      <div className="card summary-card">
        <span className="kicker">
          <FileText {...ICON} />
          讨论纪要
        </span>
        <h2 style={{ fontSize: 24, margin: '6px 0 4px' }}>{room?.title ?? '房间'}</h2>
        <p className="muted" style={{ margin: 0, fontSize: 13 }}>
          {room ? `${room.topicLabel} · 房主 ${room.hostName} · ${room.status === 'ended' ? '已结束' : '进行中'}` : '加载中…'}
        </p>

        <div className="summary-actions">
          {canManage ? (
            <button className="btn btn-primary btn-sm" onClick={() => generate.mutate()} disabled={generate.isPending}>
              {generate.isPending ? <RefreshCw {...ICON} className="spin" /> : <Sparkles {...ICON} />}
              {summary ? '重新生成' : '生成讨论纪要'}
            </button>
          ) : (
            <span className="dim" style={{ fontSize: 13 }}>
              纪要由房主或协管生成
            </span>
          )}
          {summary && (
            <span className="dim" style={{ fontSize: 12 }}>
              更新于 {new Date(summary.updatedAt).toLocaleString()} · 模型 {summary.model || '未配置'}
            </span>
          )}
        </div>

        {notConfigured && (
          <div className="alert" role="alert">
            <AlertCircle {...ICON} style={{ marginTop: 2, flex: '0 0 16px' }} />
            <span>
              还没配置纪要模型：请在后端 `.env` 里填好 `LLM_API_KEY`（`LLM_BASE_URL` / `LLM_MODEL` 已就绪），重启服务后再点生成。
            </span>
          </div>
        )}
        {error && !notConfigured && (
          <div className="alert" role="alert">
            <AlertCircle {...ICON} style={{ marginTop: 2, flex: '0 0 16px' }} />
            {error instanceof ApiError ? error.message : '生成失败，请稍后重试'}
          </div>
        )}

        {summaryQuery.isLoading && <p className="muted">正在读取纪要…</p>}

        {!summaryQuery.isLoading && !summary && (
          <p className="muted" style={{ marginTop: 12 }}>
            还没有纪要{canManage ? '，点上面的按钮生成' : '，等房主或协管生成后再来看'}。
          </p>
        )}

        {summary && summary.status === 'failed' && (
          <p className="muted" style={{ marginTop: 12 }}>
            上一次生成失败了{summary.error ? `（${summary.error}）` : ''}，可以再试一次。
          </p>
        )}

        {summary && summary.status === 'ready' && (
          <article className="summary-body">{summary.content}</article>
        )}

        {!user && (
          <p className="dim" style={{ marginTop: 12, fontSize: 12 }}>
            登录后才能查看本房间纪要。
          </p>
        )}
      </div>
    </div>
  )
}
