import { AlertTriangle, CalendarX2, ChevronLeft, ChevronRight, Compass, Hash, Layers, Lock, Plus, RefreshCw, SearchX, Users } from 'lucide-react'
import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { ApiError } from '../api/http'
import { TOPIC_OPTIONS, type RoomStatus, type Topic } from '../api/rooms'
import FlowField from '../components/FlowField'
import ThinkerStatue from '../components/ThinkerStatue'
import RoomCard from '../components/RoomCard'
import { useSession } from '../hooks/useSession'
import { useRooms } from '../hooks/useRooms'

const PAGE_SIZE = 20
const ICON = { size: 14, strokeWidth: 1.75 } as const

const STATUS_TABS: { value: RoomStatus | 'all'; label: string; icon: React.ReactNode }[] = [
  { value: 'active', label: '进行中', icon: <Compass {...ICON} /> },
  { value: 'ended', label: '已结束', icon: <CalendarX2 {...ICON} /> },
  { value: 'all', label: '全部', icon: <Layers {...ICON} /> },
]

/** 首页/列表页：hero（Canvas 流场 + 逐字标题）+ 筛选 + 房间网格（功能页 F-01）。 */
export default function RoomsPage() {
  const { user } = useSession()
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const [status, setStatus] = useState<RoomStatus | 'all'>('active')
  const [topic, setTopic] = useState<Topic | ''>('')
  const [page, setPage] = useState(0)

  const mine = params.get('mine') === '1'  // 与侧边栏「我的房间」同源，可直接分享 /?mine=1
  const { data, isLoading, isError, error, refetch, isFetching } = useRooms({
    status,
    topic: topic || undefined,
    mine,
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
  })

  const rooms = data?.rooms ?? []
  const total = data?.total ?? 0
  const filtered = status !== 'active' || topic !== '' || mine
  const hasNext = (page + 1) * PAGE_SIZE < total
  const statusLabel = STATUS_TABS.find((tab) => tab.value === status)?.label ?? '进行中'
  // 错误分三类呈现：未登录（401）/ 连不上后端 / 其它（见 docs/04-style/global-style.md 错误呈现规范）
  const apiError = error instanceof ApiError ? error : null
  const needLogin = apiError?.status === 401

  const toggleMine = () => {
    if (!user) {
      navigate('/login?returnTo=/')
      return
    }
    const next = new URLSearchParams(params)
    if (mine) next.delete('mine')
    else next.set('mine', '1')
    setParams(next)
    setPage(0)
  }

  const title = ['学', '习', '讨', '论', '室']

  return (
    <div>
      <div className="toolbar">
        <div className="chipset">
          {STATUS_TABS.map((tab) => (
            <button
              key={tab.value}
              className={status === tab.value ? 'on' : ''}
              onClick={() => {
                setStatus(tab.value)
                setPage(0)
              }}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>

        <select
          className="select"
          style={{ width: 180 }}
          value={topic}
          onChange={(e) => {
            setTopic(e.target.value as Topic | '')
            setPage(0)
          }}
        >
          <option value="">全部主题</option>
          {TOPIC_OPTIONS.map((item) => (
            <option key={item.value} value={item.value}>
              {item.label}
            </option>
          ))}
        </select>

        <button className={`btn btn-sm${mine ? ' btn-primary' : ''}`} onClick={toggleMine} aria-pressed={mine}>
          <Users {...ICON} />
          只看我的
        </button>

        <button className="btn btn-sm" onClick={() => refetch()} disabled={isFetching}>
          <RefreshCw {...ICON} />
          刷新
        </button>

        <div style={{ flex: 1 }} />

        <button className="btn btn-primary" onClick={() => navigate(user ? '/rooms/new' : '/login?returnTo=/rooms/new')}>
          <Plus {...ICON} size={16} />
          创建房间
        </button>
      </div>

      <section className="hero">
        <FlowField />
        <ThinkerStatue />
        <div className="hero-inner">
          <span className="kicker">
            <Hash {...ICON} />
            实时多人学习讨论空间
          </span>
          <h1 className="display">
            {title.map((char, index) => (
              <span className="ch" key={char} style={{ ['--i' as string]: index }}>
                {char}
              </span>
            ))}
            <br />
            <em>think together</em>
          </h1>
          <p className="hero-sub">
            面向一门学习主题的多人音视频讨论室：等候室审批、三种角色、举手与焦点发言、屏幕共享与课后纪要。
            现在可以创建房间、申请加入，并在房间结束后回看整场讨论记录。
          </p>
          <div className="stats">
            <div>
              <div className="stat-value">{total}</div>
              <div className="stat-label">房间数</div>
            </div>
            <div>
              <div className="stat-value">{statusLabel}</div>
              <div className="stat-label">当前筛选</div>
            </div>
            <div>
              <div className="stat-value">{mine ? '仅我的' : '全部'}</div>
              <div className="stat-label">范围</div>
            </div>
          </div>
        </div>
      </section>

      {isLoading && (
        <div className="room-grid">
          <div className="skeleton" />
          <div className="skeleton" />
          <div className="skeleton" />
        </div>
      )}

      {isError && needLogin && (
        <div className="empty">
          <span className="icon-ring">
            <Lock size={20} strokeWidth={1.75} />
          </span>
          <div>
            <h3 style={{ fontSize: 18 }}>请先登录</h3>
            <p className="muted" style={{ margin: '4px 0 0', fontSize: 14 }}>
              「我的房间」需要登录后才能查看。
            </p>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-primary" onClick={() => navigate(`/login?returnTo=${encodeURIComponent('/?mine=1')}`)}>
              去登录
            </button>
            <button
              className="btn"
              onClick={() => {
                setParams(new URLSearchParams())
                setPage(0)
              }}
            >
              看全部房间
            </button>
          </div>
        </div>
      )}

      {isError && !needLogin && (
        <div className="card">
          <div className="alert" role="alert">
            <AlertTriangle size={16} strokeWidth={1.75} style={{ marginTop: 2, flex: '0 0 16px' }} />
            服务暂时不可用：{apiError?.message ?? '未知错误'}。请稍后重试。
          </div>
          <button className="btn" style={{ marginTop: 12 }} onClick={() => refetch()}>
            <RefreshCw {...ICON} />
            重试
          </button>
        </div>
      )}

      {!isLoading && !isError && rooms.length === 0 && (
        <div className="empty">
          <span className="icon-ring">{filtered ? <SearchX size={20} strokeWidth={1.75} /> : <Plus size={20} strokeWidth={1.75} />}</span>
          <div>
            <h3 style={{ fontSize: 18 }}>{filtered ? '没有符合条件的房间' : '还没有房间'}</h3>
            <p className="muted" style={{ margin: '4px 0 0', fontSize: 14 }}>
              {filtered ? '试试切换主题或状态筛选' : '点击右上角创建第一个学习讨论室'}
            </p>
          </div>
          {filtered ? (
            <button
              className="btn"
              onClick={() => {
                setStatus('active')
                setTopic('')
                setParams(new URLSearchParams())
                setPage(0)
              }}
            >
              清空筛选
            </button>
          ) : (
            <button className="btn btn-primary" onClick={() => navigate(user ? '/rooms/new' : '/login?returnTo=/rooms/new')}>
              <Plus {...ICON} size={16} />
              创建房间
            </button>
          )}
        </div>
      )}

      {rooms.length > 0 && (
        <div className="room-grid">
          {rooms.map((room, index) => (
            <RoomCard key={room.id} room={room} index={index} />
          ))}
        </div>
      )}

      {total > PAGE_SIZE && (
        <div className="pager">
          <button className="btn btn-sm" disabled={page === 0} onClick={() => setPage((value) => Math.max(0, value - 1))}>
            <ChevronLeft {...ICON} />
            上一页
          </button>
          <span className="dim tnum" style={{ fontSize: 13 }}>
            第 {page + 1} / {Math.ceil(total / PAGE_SIZE)} 页 · 共 {total} 个房间
          </span>
          <button className="btn btn-sm" disabled={!hasNext} onClick={() => setPage((value) => value + 1)}>
            下一页
            <ChevronRight {...ICON} />
          </button>
        </div>
      )}
    </div>
  )
}
