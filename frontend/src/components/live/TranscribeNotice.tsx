/** 进房一次性告知（r010 R6 隐私；ADR-0023 D4 如实表述）+ 自动收起。
 *
 * 口径（用户 2026-09-20 确认）：音频会经 LiveKit 云与识别服务商；**关掉麦克风即不参与转写**。
 * 自动收起时长读 CSS 令牌 `--transcribe-notice-ms`（单点可调）；「知道了」后本机记住不再弹。
 */
import { Info } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

const STORAGE_KEY = 'lg.transcribe.notice.dismissed'

function readNoticeMs(): number {
  const raw = getComputedStyle(document.documentElement).getPropertyValue('--transcribe-notice-ms').trim()
  const value = Number(raw)
  return Number.isFinite(value) && value > 0 ? value : 30000
}

interface Props {
  /** 点「关掉我的麦克风」：直接关本端麦克风（= 不参与转写）。 */
  onMicOff: () => void
}

export default function TranscribeNotice({ onMicOff }: Props) {
  const [open, setOpen] = useState(() => window.localStorage.getItem(STORAGE_KEY) !== '1')

  const dismiss = useCallback((remember: boolean) => {
    if (remember) window.localStorage.setItem(STORAGE_KEY, '1')
    setOpen(false)
  }, [])

  useEffect(() => {
    if (!open) return
    const timer = window.setTimeout(() => dismiss(false), readNoticeMs())
    return () => window.clearTimeout(timer)
  }, [open, dismiss])

  if (!open) return null
  return (
    <div className="transcribe-notice" role="status">
      <Info size={14} aria-hidden />
      <span className="transcribe-notice-text">
        本房间会把说的话转成文字，供大家与纪要使用。音频会经 LiveKit 云与识别服务商处理，不留存录音；关掉麦克风即不参与转写。
      </span>
      <button
        className="btn btn-sm"
        onClick={() => {
          onMicOff()
          dismiss(true)
        }}
      >
        关掉我的麦克风
      </button>
      <button className="btn btn-ghost btn-sm" onClick={() => dismiss(true)}>
        知道了
      </button>
    </div>
  )
}
