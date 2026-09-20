/** 房内麦克风状态表（r006，ADR-0017 D1）。
 *
 * 为什么要单独订阅：`useTracks` 只在**轨道集合**变化时重渲染，静音 / 取消静音不算集合变化，
 * 所以「他人格子上的麦徽标」必须自己监听静音相关事件。
 *
 * 输出：`identity → isMicrophoneEnabled`（本人也在表里）；订阅失败/未连接时返回空表，
 * 调用方按 `participant.isMicrophoneEnabled` 兜底。
 */
import { useEffect, useState } from 'react'
import { Room, RoomEvent } from 'livekit-client'

const MIC_EVENTS = [
  RoomEvent.TrackMuted,
  RoomEvent.TrackUnmuted,
  RoomEvent.TrackPublished,
  RoomEvent.TrackUnpublished,
  RoomEvent.TrackSubscribed,
  RoomEvent.TrackUnsubscribed,
  RoomEvent.ParticipantConnected,
  RoomEvent.ParticipantDisconnected,
  RoomEvent.LocalTrackPublished,
  RoomEvent.LocalTrackUnpublished,
] as const

export function useMicStates(room: Room | null): Record<string, boolean> {
  const [states, setStates] = useState<Record<string, boolean>>({})

  useEffect(() => {
    if (!room) return
    const sync = () => {
      const next: Record<string, boolean> = {}
      room.remoteParticipants.forEach((participant) => {
        next[participant.identity] = participant.isMicrophoneEnabled
      })
      next[room.localParticipant.identity] = room.localParticipant.isMicrophoneEnabled
      setStates(next)
    }
    sync()
    MIC_EVENTS.forEach((event) => room.on(event, sync))
    return () => {
      MIC_EVENTS.forEach((event) => room.off(event, sync))
    }
  }, [room])

  return states
}
