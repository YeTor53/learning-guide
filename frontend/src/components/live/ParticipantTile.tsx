/** 单个视频格：画面或头像块 + 姓名 + 麦克风/角色徽标。
 *
 * 设计事实源：docs/02-modules/r002-livekit-features.md §4.1（交流页布局，专注感）。
 */
import { MicOff } from 'lucide-react'
import type { Participant, TrackPublication } from 'livekit-client'
import { VideoTrack } from '@livekit/components-react'

import { ROLE_LABEL, type Role } from '../../api/rooms'

const ICON = { size: 13, strokeWidth: 1.75 } as const

interface Props {
  participant: Participant
  publication?: TrackPublication
  role?: Role | null
  isFocus?: boolean
  speaking?: boolean
}

function initial(name: string): string {
  const trimmed = name.trim()
  return trimmed ? trimmed.slice(0, 1) : '?'
}

export default function ParticipantTile({ participant, publication, role, isFocus = false, speaking = false }: Props) {
  const name = participant.name || participant.identity
  const showVideo = Boolean(publication && !publication.isMuted)
  const classes = ['live-tile']
  if (isFocus) classes.push('live-tile-focus')
  if (speaking) classes.push('live-tile-speaking')

  return (
    <div className={classes.join(' ')}>
      {showVideo ? (
        <VideoTrack trackRef={{ participant, publication: publication!, source: publication!.source }} />
      ) : (
        <div className="live-tile-avatar" aria-hidden>
          {initial(name)}
        </div>
      )}
      <div className="live-tile-bar">
        <span className="live-tile-name">{name}</span>
        {role && <span className={`chip ${role === 'host' ? 'chip-warn' : 'chip-quiet'}`}>{ROLE_LABEL[role]}</span>}
        {!showVideo && <MicOff {...ICON} aria-label="麦克风未开" />}
      </div>
    </div>
  )
}
