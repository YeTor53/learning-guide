/** 转写气泡（r010）：与聊天气泡同壳（复用 `--panel-strong` / 圆角 / 入场动画），
 *  靠左侧色条与麦克风图标区分；时长来自 segment 的 start/end（未知时不显示）。
 *  设计事实源：`docs/rounds/r010-transcription/design.md` §3.2。
 */
import { Mic } from 'lucide-react'

import type { SpeechLine } from '../../hooks/useTranscription'

function mmss(ms: number): string {
  const total = Math.max(0, Math.round(ms / 1000))
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`
}

interface Props {
  line: SpeechLine
  /** 渐进文本（未定稿）：显示「识别中…」 */
  live?: boolean
}

export default function SpeechBubble({ line, live = false }: Props) {
  return (
    <div className="chat-row">
      <div className={`chat-bubble chat-bubble-speech${live ? ' chat-bubble-speech-live' : ''}`}>
        <span className="chat-who">
          <Mic className="speech-mic" size={14} aria-hidden />
          {line.speakerName}
        </span>
        <span className="chat-body">{line.text}</span>
        <span className="chat-meta">
          {live && <span className="chat-time">识别中…</span>}
          {!live && line.durationMs > 1000 && <span className="chat-time">{mmss(line.durationMs)}</span>}
        </span>
      </div>
    </div>
  )
}
