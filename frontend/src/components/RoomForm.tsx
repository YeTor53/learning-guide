import { AlertTriangle, AlignLeft, ArrowRight, PenLine, Tag } from 'lucide-react'
import { useState } from 'react'

import { ApiError } from '../api/http'
import { TOPIC_OPTIONS, type CreateRoomBody, type Topic } from '../api/rooms'
import TopicPicker from './TopicPicker'

interface Props {
  submitting: boolean
  error: unknown
  onSubmit: (body: CreateRoomBody) => void
}

const ICON = { size: 14, strokeWidth: 1.75 } as const

/** 建房表单（功能页 F-02）：主题（自定义需填主题名）、标题 1–80、简介 ≤500。 */
export default function RoomForm({ submitting, error, onSubmit }: Props) {
  const [topic, setTopic] = useState<Topic>('epicureanism')
  const [topicLabel, setTopicLabel] = useState('伊壁鸠鲁主义')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [localError, setLocalError] = useState<string | null>(null)

  const pickTopic = (value: Topic) => {
    setTopic(value)
    const preset = TOPIC_OPTIONS.find((item) => item.value === value)
    setTopicLabel(value === 'custom' ? '' : (preset?.label ?? ''))
  }

  const submit = (event: React.FormEvent) => {
    event.preventDefault()
    if (!title.trim()) return setLocalError('请输入标题')
    if (title.trim().length > 80) return setLocalError('标题最多 80 字')
    if (!topicLabel.trim()) return setLocalError('请填写主题名')
    if (description.length > 500) return setLocalError('简介最多 500 字')
    setLocalError(null)
    onSubmit({ topic, topicLabel: topicLabel.trim(), title: title.trim(), description })
  }

  const message = localError ?? (error instanceof ApiError ? error.message : error ? '创建失败，请稍后重试' : null)

  return (
    <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {message && (
        <div className="alert" role="alert">
          <AlertTriangle size={16} strokeWidth={1.75} style={{ marginTop: 2, flex: '0 0 16px' }} />
          {message}
        </div>
      )}

      <div className="field">
        <label>
          <Tag {...ICON} style={{ verticalAlign: -2, marginRight: 6 }} />
          学习主题
        </label>
        <TopicPicker value={topic} onChange={pickTopic} />
        <span className="hint">主题决定房间的分类与展示标签</span>
      </div>

      {topic === 'custom' && (
        <div className="field">
          <label htmlFor="room-topic-label">主题名</label>
          <input id="room-topic-label" className="input" value={topicLabel} onChange={(e) => setTopicLabel(e.target.value)} placeholder="给你的主题起个名字" />
        </div>
      )}

      <div className="field">
        <label htmlFor="room-title">
          <PenLine {...ICON} style={{ verticalAlign: -2, marginRight: 6 }} />
          标题
        </label>
        <input id="room-title" className="input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="这次想讨论什么" />
        <span className="hint">{title.trim().length}/80 字</span>
      </div>

      <div className="field">
        <label htmlFor="room-description">
          <AlignLeft {...ICON} style={{ verticalAlign: -2, marginRight: 6 }} />
          简介
        </label>
        <textarea
          id="room-description"
          className="textarea"
          value={description}
          placeholder="想讨论什么？打算怎么进行？留几句话给加入的人"
          onChange={(e) => setDescription(e.target.value)}
        />
        <span className="hint">{description.length}/500 字</span>
      </div>

      <button className="btn btn-primary" type="submit" disabled={submitting}>
        <ArrowRight {...ICON} size={16} />
        {submitting ? '创建中…' : '创建房间'}
      </button>
    </form>
  )
}
