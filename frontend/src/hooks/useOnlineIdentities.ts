/** 在场 identity 列表（SDK 事件驱动，不走库成员表）。用于抽屉里区分「在线 / 离线」。
 *
 * r010：**排除房间里的 agent**（转写 worker 也是 LiveKit 参与者，identity 形如 `agent-xxxx`）——
 * 它不该出现在舞台格子里，也不该被算作「成员在线」。判据双保险：identity 前缀 + `kind`。
 */
import { useEffect, useState } from 'react'
import { Room, RoomEvent } from 'livekit-client'

export const AGENT_IDENTITY_PREFIX = 'agent-'

/** 是不是房间里的 agent（转写 worker 等）：前缀或 SDK 的 participant kind 任一命中即算。 */
export function isAgentParticipant(participant: { identity?: string; kind?: unknown } | null | undefined): boolean {
  if (!participant) return false
  if ((participant.identity ?? '').startsWith(AGENT_IDENTITY_PREFIX)) return true
  const kind = String(participant.kind ?? '')
  return kind.toUpperCase().includes('AGENT')
}

function snapshot(room: Room): string[] {
  const locals = room.localParticipant?.identity ? [room.localParticipant.identity] : []
  const remotes = [...room.remoteParticipants.values()]
    .filter((p) => !isAgentParticipant(p))
    .map((p) => p.identity)
  return [...locals, ...remotes].filter(Boolean) as string[]
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
