/** 当前说话者（用于舞台的单焦点布局）。无人在说时返回 null。 */
import { useEffect, useState } from 'react'
import { Participant, Room, RoomEvent } from 'livekit-client'

export function useActiveSpeaker(room: Room): Participant | null {
  const [speaker, setSpeaker] = useState<Participant | null>(null)

  useEffect(() => {
    const onChange = (speakers: Participant[]) => setSpeaker(speakers[0] ?? null)
    room.on(RoomEvent.ActiveSpeakersChanged, onChange)
    return () => {
      room.off(RoomEvent.ActiveSpeakersChanged, onChange)
    }
  }, [room])

  return speaker
}
