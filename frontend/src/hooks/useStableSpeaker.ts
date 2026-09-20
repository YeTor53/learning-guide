/** 说话者焦点防抽播（r009，motion-design C4）。
 *
 * 规则：① 说话者需连续 `--speaker-debounce-ms` 保持才被采纳 ② 采纳后 `--speaker-cooldown-ms` 内不再切换
 * ③ 手动焦点设置后 `--focus-hold-ms` 内**压制自动焦点**（人工意图优先）。
 * 目的：两人轮流说话时画面不再每几百毫秒抽一下（实测目标：30 秒内焦点切换 ≤3 次）。
 */
import { useEffect, useRef, useState } from 'react'

import { prefersReducedMotion, readToken } from './useFlipTransition'

export interface StableSpeakerOptions {
  /** 手动焦点者（在册且 active）；非空时进入保护期。 */
  manualFocusId?: string | null
  debounceMs?: number
  cooldownMs?: number
  holdMs?: number
}

export function useStableSpeaker(rawSpeakerId: string | null, options: StableSpeakerOptions = {}): string | null {
  const debounceMs = options.debounceMs ?? readToken('--speaker-debounce-ms', 800)
  const cooldownMs = options.cooldownMs ?? readToken('--speaker-cooldown-ms', 3000)
  const holdMs = options.holdMs ?? readToken('--focus-hold-ms', 10000)
  const manualFocusId = options.manualFocusId ?? null
  const [accepted, setAccepted] = useState<string | null>(null)
  const lastSwitchAt = useRef(0)
  const manualSince = useRef<number | null>(null)

  // 手动焦点出现 → 记下时刻并立刻清空自动焦点（人工优先）
  useEffect(() => {
    if (manualFocusId) {
      manualSince.current = Date.now()
      setAccepted(null)
    }
  }, [manualFocusId])

  useEffect(() => {
    if (manualFocusId) return
    if (prefersReducedMotion()) {
      setAccepted(rawSpeakerId)
      return
    }
    if (!rawSpeakerId) {
      // 没人说话：保留当前焦点一小会儿（避免静音间隙闪回均分），由冷却时长兜住
      return
    }
    if (rawSpeakerId === accepted) return
    const withinHold = manualSince.current !== null && Date.now() - manualSince.current < holdMs
    if (withinHold) return
    const timer = window.setTimeout(() => {
      const since = Date.now() - lastSwitchAt.current
      if (lastSwitchAt.current !== 0 && since < cooldownMs) return
      lastSwitchAt.current = Date.now()
      setAccepted(rawSpeakerId)
    }, debounceMs)
    return () => window.clearTimeout(timer)
  }, [rawSpeakerId, accepted, manualFocusId, debounceMs, cooldownMs, holdMs])

  return accepted
}
