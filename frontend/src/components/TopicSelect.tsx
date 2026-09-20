/** 主题筛选：自绘下拉（r007 Q3=1）。
 *
 * 为什么不用原生 `<select>`：浏览器默认浅色外观 + 系统字体 + 自带箭头，与暗色编辑风冲突（redirect-01 §2）。
 * 形态：按钮（当前项 + 图标 + 折角）+ 暗色面板（`role="listbox"`，每项带图标）；
 * 交互：点击开合、`Esc` 关闭并回焦、点击面板外关闭、`↑/↓` 移动、`Enter/Space` 选中。
 */
import { useEffect, useRef, useState } from 'react'
import { ChevronDown } from 'lucide-react'

import type { Topic } from '../api/rooms'
import { TOPIC_ICONS } from './topicIcons'

interface Option {
  value: Topic | ''
  label: string
}

interface Props {
  value: Topic | ''
  options: Option[]
  onChange: (value: Topic | '') => void
  /** 无障碍名（默认「主题筛选」）。 */
  label?: string
}

export default function TopicSelect({ value, options, onChange, label = '主题筛选' }: Props) {
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(() => Math.max(0, options.findIndex((item) => item.value === value)))
  const rootRef = useRef<HTMLDivElement | null>(null)
  const buttonRef = useRef<HTMLButtonElement | null>(null)

  const current = options.find((item) => item.value === value) ?? options[0]

  useEffect(() => {
    if (!open) return
    const onPointerDown = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false)
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false)
        buttonRef.current?.focus()
      }
    }
    document.addEventListener('pointerdown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('pointerdown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  const choose = (next: Topic | '') => {
    onChange(next)
    setOpen(false)
    buttonRef.current?.focus()
  }

  const onListKeyDown = (event: React.KeyboardEvent) => {
    if (!open) return
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setActive((index) => Math.min(options.length - 1, index + 1))
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setActive((index) => Math.max(0, index - 1))
    } else if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      choose(options[active]?.value ?? '')
    }
  }

  const CurrentIcon = current && current.value !== '' ? TOPIC_ICONS[current.value as Topic] : null

  return (
    <div className="topic-select" ref={rootRef} onKeyDown={onListKeyDown}>
      <button
        ref={buttonRef}
        type="button"
        className={`topic-select-btn${open ? ' open' : ''}`}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={label}
        onClick={() => {
          setActive(Math.max(0, options.findIndex((item) => item.value === value)))
          setOpen((v) => !v)
        }}
        onKeyDown={(event) => {
          if (!open && (event.key === 'ArrowDown' || event.key === 'Enter' || event.key === ' ')) {
            event.preventDefault()
            setActive(Math.max(0, options.findIndex((item) => item.value === value)))
            setOpen(true)
          }
        }}
      >
        {CurrentIcon && <CurrentIcon size={15} strokeWidth={1.75} className="topic-icon" />}
        <span className="topic-select-label">{current?.label ?? '全部主题'}</span>
        <ChevronDown size={15} strokeWidth={1.75} className={`topic-select-caret${open ? ' on' : ''}`} />
      </button>

      {open && (
        <div className="topic-select-panel" role="listbox" tabIndex={-1} aria-label={label}>
          {options.map((item, index) => {
            const Icon = item.value === '' ? null : TOPIC_ICONS[item.value as Topic]
            const selected = item.value === value
            return (
              <button
                key={item.value || 'all'}
                type="button"
                role="option"
                aria-selected={selected}
                className={`topic-select-item${selected ? ' on' : ''}${index === active ? ' active' : ''}`}
                onMouseEnter={() => setActive(index)}
                onClick={() => choose(item.value)}
              >
                <span className="topic-select-item-icon">{Icon ? <Icon size={15} strokeWidth={1.75} /> : null}</span>
                <span>{item.label}</span>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
