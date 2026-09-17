import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { TOPIC_OPTIONS, type RoomStatus, type Topic } from '../api/rooms'
import RoomCard from '../components/RoomCard'
import { useSession } from '../hooks/useSession'
import { useRooms } from '../hooks/useRooms'

const PAGE_SIZE = 20

export default function RoomsPage() {
  const { user } = useSession()
  const navigate = useNavigate()
  const [status, setStatus] = useState<RoomStatus | 'all'>('active')
  const [topic, setTopic] = useState<Topic | ''>('')
  const [mine, setMine] = useState(false)
  const [page, setPage] = useState(0)

  const { data, isLoading, isError, refetch } = useRooms({
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

  const toggleMine = () => {
    if (!user) {
      navigate('/login?returnTo=/')
      return
    }
    setMine((value) => !value)
    setPage(0)
  }

  return (
    <div className="stack">
      <div className="spread">
        <h1 style={{ margin: 0 }}>学习讨论室</h1>
        <button className="primary" onClick={() => navigate(user ? '/rooms/new' : '/login?returnTo=/rooms/new')}>
          创建房间
        </button>
      </div>

      <div className="card stack">
        <div className="filters tabs">
          {(['active', 'ended', 'all'] as const).map((value) => (
            <button
              key={value}
              className={status === value ? 'on' : ''}
              onClick={() => {
                setStatus(value)
                setPage(0)
              }}
            >
              {value === 'active' ? '进行中' : value === 'ended' ? '已结束' : '全部'}
            </button>
          ))}
          <select
            value={topic}
            style={{ width: 180 }}
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
          <label className="row" style={{ gap: 6 }}>
            <input type="checkbox" checked={mine} onChange={toggleMine} style={{ width: 'auto' }} />
            只看我的
          </label>
        </div>
      </div>

      {isLoading && (
        <div className="stack">
          <div className="skeleton" />
          <div className="skeleton" />
          <div className="skeleton" />
        </div>
      )}

      {isError && (
        <div className="card">
          <div className="errorbar">房间列表加载失败，请检查后端是否已启动</div>
          <button style={{ marginTop: 8 }} onClick={() => refetch()}>
            重试
          </button>
        </div>
      )}

      {!isLoading && !isError && rooms.length === 0 && (
        <div className="card">
          {filtered ? (
            <>
              <p className="muted">没有符合条件的房间，试试切换主题或状态筛选</p>
              <button
                onClick={() => {
                  setStatus('active')
                  setTopic('')
                  setMine(false)
                  setPage(0)
                }}
              >
                清空筛选
              </button>
            </>
          ) : (
            <>
              <p className="muted">还没有房间，点击右上角创建第一个学习讨论室</p>
              <Link to={user ? '/rooms/new' : '/login?returnTo=/rooms/new'}>
                <button className="primary">创建房间</button>
              </Link>
            </>
          )}
        </div>
      )}

      {rooms.map((room) => (
        <RoomCard key={room.id} room={room} />
      ))}

      {total > PAGE_SIZE && (
        <div className="row" style={{ justifyContent: 'center' }}>
          <button disabled={page === 0} onClick={() => setPage((value) => Math.max(0, value - 1))}>
            上一页
          </button>
          <span className="muted">
            第 {page + 1} / {Math.ceil(total / PAGE_SIZE)} 页 · 共 {total} 个房间
          </span>
          <button disabled={!hasNext} onClick={() => setPage((value) => value + 1)}>
            下一页
          </button>
        </div>
      )}
    </div>
  )
}
