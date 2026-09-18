/** 在场 identity 列表（SDK 事件驱动，不走库成员表）。用于抽屉里区分「在线 / 离线」。 */
import { useEffect, useState } from 'react'
import { Room, RoomEvent } from 'livekit-client'

function snapshot(room: Room): string[] {
  return [room.localParticipant?.identity, ...room.remoteParticipants.keys()].filter(Boolean) as string[]
}

export function useOnlineIdentities(room: Room, status: string): string[] {
  const [ids, setIds] = useState<string[]>([])

  useEffect(() => {
    const update = () => setIds(snapshot(room))
    if (status === 'connected' || status === 'reconnecting') update()
    else if (status === 'closed' || status === 'idle') setIds([])
    room
      .on(RoomEvent.ParticipantConnected, update)
      .on(RoomEvent.ParticipantDisconnected, update)
      .on(RoomEvent.Connected, update)
    return () => {
      room
        .off(RoomEvent.ParticipantConnected, update)
        .off(RoomEvent.ParticipantDisconnected, update)
        .off(RoomEvent.Connected, update)
    }
  }, [room, status])

  return ids
}
