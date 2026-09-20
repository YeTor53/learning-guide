/** 管理后台（r012）：房间 / 用户 / 纪要 / 审计 四张列表 + 三动作。
 *
 * 入口：侧边栏「管理后台」（**仅超管可见**，Q12=2）。服务端仍强制鉴权：
 * 401 → 去登录（带 returnTo=/admin）；403 → 明确提示「只有管理员能进这里」。
 * 删除/结束/重生纪要都是服务端动作，成功后失效列表与审计（见 useAdmin.ts）。
 */
import { CalendarRange, ClipboardList, RefreshCw, Search, ShieldCheck, Users } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { ApiError } from '../api/http'
import AdminAuditTable from '../components/admin/AdminAuditTable'
import AdminRoomTable from '../components/admin/AdminRoomTable'
import AdminSummaryTable from '../components/admin/AdminSummaryTable'
import AdminUserTable from '../components/admin/AdminUserTable'
import { useAdminActions, useAdminAudit, useAdminRooms, useAdminSummaries, useAdminUsers } from '../hooks/useAdmin'
import { useSession } from '../hooks/useSession'

type Tab = 'rooms' | 'users' | 'summaries' | 'audit'

const PAGE_SIZE = 20
const ICON = { size: 14, strokeWidth: 1.75 } as const

const TABS: { value: Tab; label: string; icon: React.ReactNode }[] = [
  { value: 'rooms', label: '房间', icon: <CalendarRange {...ICON} /> },
  { value: 'users', label: '用户', icon: <Users {...ICON} /> },
  { value: 'summaries', label: '纪要', icon: <ClipboardList {...ICON} /> },
  { value: 'audit', label: '审计', icon: <ShieldCheck {...ICON} /> },
]

export default function AdminPage() {
  const navigate = useNavigate()
  const { user, isLoading: sessionLoading } = useSession()
  const [tab, setTab] = useState<Tab>('rooms')
  const [keyword, setKeyword] = useState('')
  const [onlineOnly, setOnlineOnly] = useState(false)
  const [page, setPage] = useState(0)
  const [confirmId, setConfirmId] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const offset = page * PAGE_SIZE
  const rooms = useAdminRooms({ q: keyword || undefined, limit: PAGE_SIZE, offset })
  const users = useAdminUsers({ q: keyword || undefined, online_only: onlineOnly ? 1 : undefined, limit: PAGE_SIZE, offset })
  const summaries = useAdminSummaries({ limit: PAGE_SIZE, offset })
  const audit = useAdminAudit({ limit: PAGE_SIZE, offset })
  const { endRoom, deleteRoom, regenerateSummary } = useAdminActions()

  const active = tab === 'rooms' ? rooms : tab === 'users' ? users : tab === 'summaries' ? summaries : audit
  const apiError = active.error instanceof ApiError ? active.error : null
  const needLogin = apiError?.status === 401
  const forbidden = apiError?.status === 403
  const busyId =
    (endRoom.isPending && endRoom.variables) ||
    (regenerateSummary.isPending && regenerateSummary.variables) ||
    (deleteRoom.isPending && deleteRoom.variables) ||
    null

  const switchTab = (next: Tab) => {
    setTab(next)
    setPage(0)
    setKeyword('')
    setNotice(null)
  }

  const endRoomById = (roomId: string) => {
    setNotice(null)
    endRoom.mutate(roomId, {
      onSuccess: () => setNotice('已结束该房间'),
      onError: (error) => setNotice(error instanceof ApiError ? error.message : '结束房间失败'),
    })
  }

  const deleteRoomById = (roomId: string) => {
    setConfirmId(null)
    deleteRoom.mutate(roomId, {
      onSuccess: () => setNotice('已删除该房间（不可恢复）'),
      onError: (error) => setNotice(error instanceof ApiError ? error.message : '删除房间失败'),
    })
  }

  const regenerate = (roomId: string) => {
    setNotice('正在生成纪要，请稍候…')
    regenerateSummary.mutate(roomId, {
      onSuccess: (data) => setNotice(data.status === 'ready' ? '纪要已生成' : '纪要生成未成功'),
      onError: (error) => setNotice(error instanceof ApiError ? error.message : '生成纪要失败'),
    })
  }

  if (!sessionLoading && user && user.role !== 'superadmin') {
    return (
      <div className="card admin-guard">
        <p>只有管理员能进这里。</p>
        <Link className="btn btn-sm" to="/">
          回房间列表
        </Link>
      </div>
    )
  }

  return (
    <section className="admin-page">
      <header className="admin-head">
        <div>
          <p className="kicker">平台管理</p>
          <h1 className="detail-title">管理后台</h1>
          <p className="dim">{apiError ? active.error?.message : `共 ${active.data?.total ?? 0} 条`}</p>
        </div>
        <div className="admin-tools">
          {tab !== 'summaries' && tab !== 'audit' && (
            <label className="admin-search">
              <Search {...ICON} />
              <input
                className="input"
                value={keyword}
                placeholder={tab === 'rooms' ? '搜房间标题 / 房间码 / 房主' : '搜邮箱 / 显示名'}
                onChange={(event) => {
                  setKeyword(event.target.value)
                  setPage(0)
                }}
              />
            </label>
          )}
          {tab === 'users' && (
            <button
              className={`btn btn-sm${onlineOnly ? ' btn-primary' : ''}`}
              aria-pressed={onlineOnly}
              onClick={() => {
                setOnlineOnly((value) => !value)
                setPage(0)
              }}
            >
              只看在线
            </button>
          )}
          <button className="btn btn-sm btn-ghost" onClick={() => void active.refetch()} disabled={active.isFetching}>
            <RefreshCw {...ICON} className={active.isFetching ? 'spin' : undefined} />
            刷新
          </button>
        </div>
      </header>

      <div className="live-drawer-tabs admin-tabs" role="tablist" aria-label="后台分区">
        {TABS.map((item) => (
          <button
            key={item.value}
            role="tab"
            aria-selected={tab === item.value}
            className={`live-drawer-tab${tab === item.value ? ' on' : ''}`}
            onClick={() => switchTab(item.value)}
          >
            {item.icon}
            {item.label}
          </button>
        ))}
      </div>

      {notice && <div className="alert alert-info admin-notice">{notice}</div>}

      {needLogin ? (
        <div className="card admin-guard">
          <p>请先登录再进管理后台。</p>
          <button className="btn btn-sm btn-primary" onClick={() => navigate('/login?returnTo=/admin')}>
            去登录
          </button>
        </div>
      ) : forbidden ? (
        <div className="card admin-guard">
          <p>只有管理员能进这里。</p>
          <Link className="btn btn-sm" to="/">
            回房间列表
          </Link>
        </div>
      ) : active.isLoading ? (
        <p className="empty dim">正在加载…</p>
      ) : active.isError ? (
        <div className="card admin-guard">
          <p>{apiError?.message ?? '服务暂时不可用'}</p>
          <button className="btn btn-sm" onClick={() => void active.refetch()}>
            重试
          </button>
        </div>
      ) : (
        <>
          {tab === 'rooms' && (
            <AdminRoomTable
              rooms={rooms.data?.items ?? []}
              busyId={busyId}
              confirmId={confirmId}
              onEnd={endRoomById}
              onDelete={deleteRoomById}
              onRegenerate={regenerate}
              onAskConfirm={setConfirmId}
            />
          )}
          {tab === 'users' && <AdminUserTable users={users.data?.items ?? []} />}
          {tab === 'summaries' && <AdminSummaryTable summaries={summaries.data?.items ?? []} />}
          {tab === 'audit' && <AdminAuditTable entries={audit.data?.items ?? []} />}

          <div className="admin-pager">
            <button className="btn btn-sm" onClick={() => setPage((value) => Math.max(0, value - 1))} disabled={page === 0}>
              上一页
            </button>
            <span className="dim">
              第 {page + 1} 页 · 共 {active.data?.total ?? 0} 条
            </span>
            <button
              className="btn btn-sm"
              onClick={() => setPage((value) => value + 1)}
              disabled={(page + 1) * PAGE_SIZE >= (active.data?.total ?? 0)}
            >
              下一页
            </button>
          </div>
        </>
      )}

      <p className="dim admin-foot">
        管理动作都会留痕：结束房间 / 删除房间 / 重生纪要各写一条流水（见「审计」分区），其中删除不可恢复。
      </p>
    </section>
  )
}
