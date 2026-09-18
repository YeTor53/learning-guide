/** 舞台：单焦点布局（说话者主格 + 其余窄缩格）。
 *
 * 设计事实源：docs/02-modules/r002-livekit-features.md §4.1、ADR-0011（在场来自 SDK）。
 */
import { Track } from 'livekit-client'
import { useTracks } from '@livekit/components-react'

import type { Member, Role } from '../../api/rooms'
import ParticipantTile from './ParticipantTile'

interface Props {
  members: Member[]
  speakerIdentity: string | null
  localIdentity: string
}

export default function LiveStage({ members, speakerIdentity, localIdentity }: Props) {
  const tracks = useTracks([{ source: Track.Source.Camera, withPlaceholder: true }], { onlySubscribed: false })
  const byIdentity = new Map(members.map((member) => [member.userId, member]))

  // 单焦点：说话者优先，其次自己
  const focusIdentity = speakerIdentity ?? localIdentity
  const focus = tracks.find((item) => item.participant.identity === focusIdentity) ?? tracks[0]
  const rail = tracks.filter((item) => item.participant.identity !== focus?.participant.identity)

  const roleOf = (identity: string): Role | null => byIdentity.get(identity)?.role ?? null

  if (tracks.length === 0) {
    return (
      <div className="live-stage live-stage-empty">
        <p className="muted">等待其他人加入</p>
      </div>
    )
  }

  return (
    <div className="live-stage">
      {focus && (
        <ParticipantTile
          participant={focus.participant}
          publication={focus.publication}
          role={roleOf(focus.participant.identity)}
          isFocus
          speaking={focus.participant.identity === speakerIdentity}
        />
      )}
      {rail.length > 0 && (
        <div className="live-rail">
          {rail.map((item) => (
            <ParticipantTile
              key={item.participant.identity}
              participant={item.participant}
              publication={item.publication}
              role={roleOf(item.participant.identity)}
              speaking={item.participant.identity === speakerIdentity}
            />
          ))}
        </div>
      )}
    </div>
  )
}
