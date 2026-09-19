/** 屏幕共享：本地开/停 + 「谁在共享」的派生 + 房主/协管的协作式停止请求。
 *
 * 设计事实源：docs/rounds/r004-room-extras/design.md §5.5、§6.2（停他人共享＝协作停止，服务端强停待实测）
 * 防呆（沿用 r002 §4.8）：共享音频默认不勾（`audio: false`），共享只由按钮手势触发。
 */
import { useCallback, useEffect, useState } from 'react'
import { Room, RoomEvent, Track } from 'livekit-client'

import { CHANNEL_TOPIC, publishSnapshot, useDataChannel } from './useDataChannel'

interface ScreenStopRequest {
  v: number
  targetUserId: string
  requestedBy: string
}

export interface ScreenShareState {
  /** 正在共享的 identity（无人共享为 null）。 */
  ownerId: string | null
  /** 自己是否在共享。 */
  sharing: boolean
  error: string | null
  /** 开始共享（必须由点击手势调用：浏览器要求用户手势）。 */
  start: () => Promise<void>
  /** 停止自己正在进行的共享。 */
  stop: () => Promise<void>
  /** 房主/协管请求某人停止共享（协作：对面收到后自己停）。 */
  requestStop: (userId: string) => Promise<void>
  /** 收到别人的停止请求时的提示（自己就是目标时）。 */
  requestedBy: string | null
  dismissRequested: () => void
}

function findScreenShareOwner(room: Room): string | null {
  const local = [...room.localParticipant.trackPublications.values()].find(
    (pub) => pub.source === Track.Source.ScreenShare && !pub.isMuted,
  )
  if (local) return room.localParticipant.identity
  for (const participant of room.remoteParticipants.values()) {
    const found = [...participant.trackPublications.values()].find(
      (pub) => pub.source === Track.Source.ScreenShare && !pub.isMuted,
    )
    if (found) return participant.identity
  }
  return null
}

export function useScreenShare(room: Room | null, status: string): ScreenShareState {
  const [ownerId, setOwnerId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [requestedBy, setRequestedBy] = useState<string | null>(null)

  useEffect(() => {
    if (!room) return
    const scan = () => setOwnerId(status === 'closed' || status === 'idle' ? null : findScreenShareOwner(room))
    scan()
    room
      .on(RoomEvent.LocalTrackPublished, scan)
      .on(RoomEvent.LocalTrackUnpublished, scan)
      .on(RoomEvent.TrackPublished, scan)
      .on(RoomEvent.TrackUnpublished, scan)
      .on(RoomEvent.TrackMuted, scan)
      .on(RoomEvent.TrackUnmuted, scan)
      .on(RoomEvent.ParticipantDisconnected, scan)
      .on(RoomEvent.Connected, scan)
    return () => {
      room
        .off(RoomEvent.LocalTrackPublished, scan)
        .off(RoomEvent.LocalTrackUnpublished, scan)
        .off(RoomEvent.TrackPublished, scan)
        .off(RoomEvent.TrackUnpublished, scan)
        .off(RoomEvent.TrackMuted, scan)
        .off(RoomEvent.TrackUnmuted, scan)
        .off(RoomEvent.ParticipantDisconnected, scan)
        .off(RoomEvent.Connected, scan)
    }
  }, [room, status])

  const stop = useCallback(async () => {
    if (!room) return
    try {
      await room.localParticipant.setScreenShareEnabled(false)
      setOwnerId(findScreenShareOwner(room))
    } catch (err) {
      setError(err instanceof Error ? err.message : '停止共享失败')
    }
  }, [room])

  // 协作式停止：只响应对自己的请求
  useDataChannel<ScreenStopRequest>(room, CHANNEL_TOPIC.screenStop, (payload) => {
    if (!room) return
    if (payload.targetUserId !== room.localParticipant.identity) return
    setRequestedBy(payload.requestedBy)
    void stop()
  })

  const requestStop = useCallback(
    async (userId: string) => {
      if (!room) return
      await publishSnapshot(room, CHANNEL_TOPIC.screenStop, {
        v: 1,
        targetUserId: userId,
        requestedBy: room.localParticipant.identity,
      })
    },
    [room],
  )

  const start = useCallback(async () => {
    if (!room) return
    try {
      // 只共享画面，不共享系统音频（防呆条②：共享音频会与麦克风互相回授）
      await room.localParticipant.setScreenShareEnabled(true, { audio: false })
      setOwnerId(findScreenShareOwner(room))
    } catch (err) {
      setError(err instanceof Error ? err.message : '共享屏幕未成功（可能被浏览器取消）')
    }
  }, [room])

  return {
    ownerId,
    sharing: !!room && ownerId === room.localParticipant.identity,
    error,
    start,
    stop,
    requestStop,
    requestedBy,
    dismissRequested: () => setRequestedBy(null),
  }
}
