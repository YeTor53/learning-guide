/** 创建房间的「学习主题」选择：带图标的卡片组（r007 Q4=1）。
 *
 * 每张卡 = 图标 + 主题名 + 一句用途（`hint`，来自 `TOPIC_OPTIONS`）；选中高亮 + 角标；
 * 用 `radio` 语义（`role="radiogroup"` / `role="radio"` + `aria-checked`），键盘 Tab + Enter/Space 可选。
 */
import { Check } from 'lucide-react'

import { TOPIC_OPTIONS, type Topic } from '../api/rooms'
import { TOPIC_ICONS } from './topicIcons'

interface Props {
  value: Topic
  onChange: (value: Topic) => void
}

export default function TopicPicker({ value, onChange }: Props) {
  return (
    <div className="topic-cards" role="radiogroup" aria-label="学习主题">
      {TOPIC_OPTIONS.map((item) => {
        const Icon = TOPIC_ICONS[item.value]
        const selected = item.value === value
        return (
          <button
            key={item.value}
            type="button"
            role="radio"
            aria-checked={selected}
            className={`topic-card${selected ? ' on' : ''}`}
            onClick={() => onChange(item.value)}
          >
            <span className="topic-card-top">
              <span className="topic-card-icon">
                <Icon size={17} strokeWidth={1.75} />
              </span>
              {selected && (
                <span className="topic-card-check" aria-hidden>
                  <Check size={13} strokeWidth={2.25} />
                </span>
              )}
            </span>
            <span className="topic-card-label">{item.label}</span>
            <span className="topic-card-hint">{item.hint}</span>
          </button>
        )
      })}
    </div>
  )
}
