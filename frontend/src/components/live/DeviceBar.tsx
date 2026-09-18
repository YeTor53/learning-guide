/** 底部悬浮控制条：只图标 + tooltip（无文字标签），专注感的做法。 */
import { Mic, MicOff, PhoneOff, Video, VideoOff } from 'lucide-react'

const ICON = { size: 20, strokeWidth: 1.75 } as const

interface Props {
  micEnabled: boolean
  camEnabled: boolean
  idle: boolean
  onToggleMic: () => void
  onToggleCam: () => void
  onLeave: () => void
}

export default function DeviceBar({ micEnabled, camEnabled, idle, onToggleMic, onToggleCam, onLeave }: Props) {
  return (
    <div className={`live-devicebar${idle ? ' live-chrome-idle' : ''}`}>
      <button
        className={`live-btn${micEnabled ? '' : ' live-btn-off'}`}
        onClick={onToggleMic}
        title={micEnabled ? '关闭麦克风' : '打开麦克风'}
        aria-label={micEnabled ? '关闭麦克风' : '打开麦克风'}
        aria-pressed={micEnabled}
      >
        {micEnabled ? <Mic {...ICON} /> : <MicOff {...ICON} />}
      </button>
      <button
        className={`live-btn${camEnabled ? '' : ' live-btn-off'}`}
        onClick={onToggleCam}
        title={camEnabled ? '关闭摄像头' : '打开摄像头'}
        aria-label={camEnabled ? '关闭摄像头' : '打开摄像头'}
        aria-pressed={camEnabled}
      >
        {camEnabled ? <Video {...ICON} /> : <VideoOff {...ICON} />}
      </button>
      <button className="live-btn live-btn-leave" onClick={onLeave} title="离开房间" aria-label="离开房间">
        <PhoneOff {...ICON} />
      </button>
    </div>
  )
}
