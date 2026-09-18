/** 三步状态时间线（等待室）：已提交 → 等待房主批准 → 进入房间；当前步暖色微亮。
 *
 * 设计事实源：docs/02-modules/r002-livekit-features.md §4.4（等待页布局，温暖感）。
 */
const STEPS = ['已提交', '等待房主批准', '进入房间'] as const

interface Props {
  /** 当前进行到第几步（0 起）。 */
  current: number
  /** 中性态（被拒 / 房间结束）时不点亮暖色。 */
  muted?: boolean
}

export default function WaitTimeline({ current, muted = false }: Props) {
  return (
    <ol className={`wait-timeline${muted ? ' wait-timeline-muted' : ''}`}>
      {STEPS.map((label, index) => {
        const done = index < current
        const active = index === current
        return (
          <li key={label} className={`wait-step${done ? ' wait-step-done' : ''}${active ? ' wait-step-active' : ''}`}>
            <span className="wait-dot" aria-hidden />
            <span className="wait-step-label">{label}</span>
          </li>
        )
      })}
    </ol>
  )
}
