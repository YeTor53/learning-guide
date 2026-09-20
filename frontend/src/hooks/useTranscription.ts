/** 转写监听与回传（r010 A 路径，ADR-0023）。
 *
 * 做什么：监听官方 `RoomEvent.TranscriptionReceived` → 渐进文本上屏（`live`）+ 最终稿并入对话流（`lines`）
 * 并把**最终稿**回传落库（幂等，多端冗余上报安全）。
 * 不做什么：不做音频采集/分段/上传（那是 B 路径；本轮不激活）；`final=false` 的中间稿不落库。
 *
 * 设计事实源：`docs/rounds/r010-transcription/design.md` §9.4。
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Room, RoomEvent } from 'livekit-client'

import { transcriptsApi, type ConversationItem, type SttMode } from '../api/transcripts'
import { isAgentParticipant } from './useOnlineIdentities'

export interface SpeechLine {
  /** 官方 segment id（= 落库幂等键）。 */
  id: string
  speakerId: string
  speakerName: string
  text: string
  durationMs: number
  /** 该段音频的开始时间（客户端近似值；排序用）。 */
  at: string
  final: boolean
}

export interface TranscriptionState {
  /** 已定稿的转写（含从库里拉的），按时间正序。 */
  lines: SpeechLine[]
  /** 正在识别中的渐进文本（未定稿，不落库）。 */
  live: SpeechLine[]
  /** 房内是否有转写 agent（`agent-*`）→ 决定「转写：开启/未开启」。 */
  agentPresent: boolean
  /** r011：本房 worker 最近一次心跳（毫秒时间戳；无则 null）。 */
  heartbeatAt: number | null
  /** r011：心跳是否新鲜（15 秒内）——与 `agentPresent` 取「或」，worker 崩了也能翻成未开启。 */
  heartbeatFresh: boolean
  /** r013：worker 最后一次错误（控制坞芯片 hover 显示，不弹 toast）。 */
  lastError: string | null
  mode: SttMode
  error: string | null
}

/** 官方 `startTime/endTime` 缺省时用这个占位时长（0 表示未知，气泡就不显示时长）。 */
const UNKNOWN_DURATION = 0

function toLine(item: ConversationItem): SpeechLine {
  return {
    id: item.meta?.externalId ?? item.id,
    speakerId: item.speakerId ?? 'unknown',
    speakerName: item.speakerName ?? item.speakerId ?? '未知',
    text: item.text,
    durationMs: item.meta?.durationMs ?? UNKNOWN_DURATION,
    at: item.at,
    final: true,
  }
}

export function useTranscription(
  room: Room | null,
  roomId: string | null,
  enabled: boolean,
  nameOf: (identity: string) => string,
): TranscriptionState {
  const [lines, setLines] = useState<SpeechLine[]>([])
  const [liveMap, setLiveMap] = useState<Record<string, SpeechLine>>({})
  const [agentPresent, setAgentPresent] = useState(false)
  const [heartbeatAt, setHeartbeatAt] = useState<number | null>(null)
  const [lastError, setLastError] = useState<string | null>(null)
  const [mode, setMode] = useState<SttMode>('off')
  const [error, setError] = useState<string | null>(null)

  const postedRef = useRef<Set<string>>(new Set())
  const nameOfRef = useRef(nameOf)
  nameOfRef.current = nameOf
  const roomIdRef = useRef(roomId)
  roomIdRef.current = roomId

  // 转写模式（只读展示用；失败不打扰用户）
  useEffect(() => {
    if (!enabled) return
    let alive = true
    transcriptsApi
      .sttStatus()
      .then((status) => {
        if (alive) setMode(status.mode)
      })
      .catch(() => undefined)
    return () => {
      alive = false
    }
  }, [enabled])

  // r011：轮询本房 worker 心跳（5 秒一次，与 LiveKit 侧参会者判据取「或」）
  useEffect(() => {
    if (!enabled || !roomId) return
    let alive = true
    const poll = () => {
      transcriptsApi
        .roomSttStatus(roomId)
        .then((status) => {
          if (!alive) return
          setHeartbeatAt(status.lastHeartbeatAt ? Date.parse(status.lastHeartbeatAt) : null)
          setLastError(status.lastError ?? null)      // r013：worker 侧错误透出
        })
        .catch(() => undefined)
    }
    poll()
    const timer = window.setInterval(poll, 5000)
    return () => {
      alive = false
      window.clearInterval(timer)
    }
  }, [enabled, roomId])

  // 库里的转写（刷新/重进与库一致；与聊天的 refresh 同口径）
  const refresh = useCallback(async () => {
    const id = roomIdRef.current
    if (!id) return
    try {
      const { items } = await transcriptsApi.conversation(id)
      setLines(items.filter((item) => item.kind === 'speech').map(toLine))
    } catch (err) {
      setError(err instanceof Error ? err.message : '转写记录加载失败')
    }
  }, [])

  useEffect(() => {
    if (enabled) void refresh()
  }, [enabled, refresh])

  // 「转写：开启/未开启」＝房间里有没有 agent（不猜、不伪装）
  useEffect(() => {
    if (!room) return
    const sync = () => {
      setAgentPresent([...room.remoteParticipants.values()].some((p) => isAgentParticipant(p)))
    }
    sync()
    room.on(RoomEvent.ParticipantConnected, sync)
    room.on(RoomEvent.ParticipantDisconnected, sync)
    // 竞态兜底（r010 实测）：本端建连早于 agent 入场时，ParticipantConnected 偶发漏刷 → 定时重算（零网络成本）
    const timer = window.setInterval(sync, 5000)
    return () => {
      room.off(RoomEvent.ParticipantConnected, sync)
      room.off(RoomEvent.ParticipantDisconnected, sync)
      window.clearInterval(timer)
    }
  }, [room])

  // 转写事件：渐进上屏 + 定稿落库
  useEffect(() => {
    if (!room || !enabled) return
    const onSegments = (segments: unknown, second?: unknown) => {
      const id = roomIdRef.current
      if (!id) return
      const speaker = second as { identity?: string; participant?: { identity?: string } } | undefined
      const speakerId = speaker?.identity ?? speaker?.participant?.identity ?? 'unknown'
      const list = Array.isArray(segments) ? (segments as Array<Record<string, unknown>>) : []
      for (const seg of list) {
        const segmentId = String(seg.id ?? '')
        if (!segmentId) continue
        const start = typeof seg.startTime === 'number' ? seg.startTime : 0
        const end = typeof seg.endTime === 'number' ? seg.endTime : 0
        const durationMs = Math.max(0, Math.round((end - start) * 1000))
        const line: SpeechLine = {
          id: segmentId,
          speakerId,
          speakerName: nameOfRef.current(speakerId),
          text: String(seg.text ?? ''),
          durationMs,
          at: new Date(Date.now() - durationMs).toISOString(),
          final: Boolean(seg.final),
        }
        if (!line.text) continue
        const key = `${speakerId}:${segmentId}`
        if (!line.final) {
          setLiveMap((prev) => ({ ...prev, [key]: line }))
          continue
        }
        setLiveMap((prev) => {
          if (!(key in prev)) return prev
          const next = { ...prev }
          delete next[key]
          return next
        })
        setLines((prev) => (prev.some((item) => item.id === segmentId) ? prev.map((item) => (item.id === segmentId ? line : item)) : [...prev, line]))
        if (postedRef.current.has(segmentId)) continue
        postedRef.current.add(segmentId)
        void transcriptsApi
          .postSegment(id, {
            externalId: segmentId,
            speakerIdentity: speakerId,
            text: line.text,
            startedAt: line.at,
            durationMs: line.durationMs,
            language: String(seg.language ?? 'zh') || 'zh',
            final: true,
          })
          .catch((err: unknown) => {
            postedRef.current.delete(segmentId)   // 允许下次同段再试（服务端幂等）
            setError(err instanceof Error ? err.message : '转写回传失败')
          })
      }
    }
    room.on(RoomEvent.TranscriptionReceived, onSegments as never)
    return () => {
      room.off(RoomEvent.TranscriptionReceived, onSegments as never)
    }
  }, [room, enabled])

  const live = useMemo(() => Object.values(liveMap).sort((a, b) => a.at.localeCompare(b.at)), [liveMap])
  const sorted = useMemo(() => lines.slice().sort((a, b) => a.at.localeCompare(b.at)), [lines])

  const heartbeatFresh = heartbeatAt !== null && Date.now() - heartbeatAt < 15_000

  return { lines: sorted, live, agentPresent, heartbeatAt, heartbeatFresh, lastError, mode, error }
}
