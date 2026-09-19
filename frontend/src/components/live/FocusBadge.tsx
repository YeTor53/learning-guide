/** 焦点格右上角的徽标：只标注**人为**的状态（共享 / 房主给的焦点）。
 *
 * 设计事实源：docs/rounds/r004-room-extras/design.md §8.3
 * 口径：复用全站 `.chip` 体系；说话者与「自己」不出现徽标（否则会噪声化）；徽标不可点击。
 */
import { Crosshair, MonitorUp } from 'lucide-react'

const ICON = { size: 14, strokeWidth: 1.75 } as const

interface Props {
  kind: 'share' | 'focus'
  name: string
  /** 是不是自己（文案写「你」）。 */
  isSelf?: boolean
}

export default function FocusBadge({ kind, name, isSelf = false }: Props) {
  const label = isSelf ? '你' : name
  return (
    <span className={`live-focus-badge chip ${kind === 'share' ? 'chip-share' : 'chip-focus'}`} role="status">
      {kind === 'share' ? <MonitorUp {...ICON} /> : <Crosshair {...ICON} />}
      {kind === 'share' ? `共享 · ${label}` : `焦点 · ${label}`}
    </span>
  )
}
