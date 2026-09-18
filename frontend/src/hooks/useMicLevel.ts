/** 本地麦克风电平（0~1）：给控制坞做「我在收音吗」的可视反馈（比颜色更可靠的防呆）。
 *
 * 实现：`localParticipant.audioLevel` 由 SDK 持续更新，这里按 ~12fps 采样并对数值做上限平滑。
 */
import { useEffect, useState } from 'react'
import { Room } from 'livekit-client'

const SAMPLE_MS = 80

export function useMicLevel(room: Room, enabled: boolean): number {
  const [level, setLevel] = useState(0)

  useEffect(() => {
    if (!enabled) {
      setLevel(0)
      return
    }
    const timer = window.setInterval(() => {
      const raw = room.localParticipant?.audioLevel ?? 0
      setLevel((prev) => Math.max(raw, prev * 0.7)) // 平滑下落，避免闪
    }, SAMPLE_MS)
    return () => window.clearInterval(timer)
  }, [room, enabled])

  return level
}
