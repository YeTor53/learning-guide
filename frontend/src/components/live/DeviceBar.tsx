/** 控制坞（交流页底部）：设备组 + 离场组，带状态点、电平反馈、快捷键与防呆规则。
 *
 * 设计事实源：docs/02-modules/r002-livekit-features.md §3 F-16（控制坞规格）、§4.5（防呆清单）、
 *             docs/04-style/global-style.md §12.1（专注感令牌）。
 * 为什么不是三个圆按钮：等形状等尺寸会让「离开」与「静音」一样容易误触，且不体现任何状态；
 * 控制坞把「设备」与「离场」分组隔开、给状态文字与电平、给确认与快捷键。
 */
import { useEffect } from 'react'
import { DoorOpen, Mic, MicOff, Settings2, Video, VideoOff } from 'lucide-react'

const ICON = { size: 18, strokeWidth: 1.75 } as const

interface Props {
  micEnabled: boolean
  camEnabled: boolean
  /** 麦克风电平 0~1（关麦时为 0）。 */
  micLevel: number
  /** 是否房主：房主不能直接离开（防呆：按钮禁用并在提示里说明）。 */
  isHost: boolean
  /** 重连中禁用所有按钮，避免「点了没反应」。 */
  disabled: boolean
  idle: boolean
  /** 是否已进入确认态（由父组件持有，便于 Esc 取消）。 */
  confirmingLeave: boolean
  onToggleMic: () => void
  onToggleCam: () => void
  onRequestLeave: () => void
  onConfirmLeave: () => void
  onCancelLeave: () => void
}

const LEVEL_BARS = 3

export default function DeviceBar({
  micEnabled,
  camEnabled,
  micLevel,
  isHost,
  disabled,
  idle,
  confirmingLeave,
  onToggleMic,
  onToggleCam,
  onRequestLeave,
  onConfirmLeave,
  onCancelLeave,
}: Props) {
  // 快捷键：M 切麦、V 切摄像头（离开不绑定快捷键——离场必须是有意的）
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null
      if (target && ['INPUT', 'TEXTAREA'].includes(target.tagName)) return
      if (disabled) return
      if (event.key === 'm' || event.key === 'M') onToggleMic()
      if (event.key === 'v' || event.key === 'V') onToggleCam()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [disabled, onToggleMic, onToggleCam])

  const level = Math.min(1, Math.max(0, micLevel))
  const activeBars = micEnabled ? Math.ceil(level * LEVEL_BARS * 4) : 0

  return (
    <div className={`live-dock${idle ? ' live-chrome-idle' : ''}`} role="toolbar" aria-label="房间控制">
      <div className="live-dock-group">
        <button
          className={`live-ctrl${micEnabled ? '' : ' live-ctrl-off'}`}
          onClick={onToggleMic}
          disabled={disabled}
          aria-pressed={micEnabled}
          title={`${micEnabled ? '关闭' : '打开'}麦克风（M）`}
        >
          {micEnabled ? <Mic {...ICON} /> : <MicOff {...ICON} />}
          <span className="live-ctrl-text">麦克风</span>
          <span className="live-ctrl-state">
            {micEnabled ? (
              <span className="live-level" aria-hidden>
                {Array.from({ length: LEVEL_BARS }).map((_, index) => (
                  <i key={index} className={index < activeBars ? 'on' : ''} />
                ))}
              </span>
            ) : (
              <span className="live-ctrl-muted">已静音</span>
            )}
          </span>
        </button>

        <button
          className={`live-ctrl${camEnabled ? '' : ' live-ctrl-off'}`}
          onClick={onToggleCam}
          disabled={disabled}
          aria-pressed={camEnabled}
          title={`${camEnabled ? '关闭' : '打开'}摄像头（V）`}
        >
          {camEnabled ? <Video {...ICON} /> : <VideoOff {...ICON} />}
          <span className="live-ctrl-text">摄像头</span>
          <span className="live-ctrl-state">{camEnabled ? '已开' : '已关'}</span>
        </button>
      </div>

      <span className="live-dock-sep" aria-hidden />

      <div className="live-dock-group">
        {confirmingLeave ? (
          <div className="live-dock-confirm" role="dialog" aria-modal="false" aria-label="确认离开">
            <span className="live-ctrl-text">离开后要重新申请才能进来，确定吗？</span>
            <button className="btn btn-danger btn-sm" onClick={onConfirmLeave}>
              确认离开
            </button>
            <button className="btn btn-ghost btn-sm" onClick={onCancelLeave}>
              取消（Esc）
            </button>
          </div>
        ) : (
          <button
            className="live-ctrl live-ctrl-leave"
            onClick={onRequestLeave}
            disabled={disabled || isHost}
            title={isHost ? '房主不能直接离开：请先移交房主或结束房间' : '离开房间（不绑定快捷键）'}
          >
            <DoorOpen {...ICON} />
            <span className="live-ctrl-text">离开</span>
          </button>
        )}
      </div>

      <span className="live-dock-hint" aria-hidden>
        <Settings2 size={12} strokeWidth={1.75} /> M 静音 · V 摄像头 · 静默 30 秒后界面淡出
      </span>
    </div>
  )
}
