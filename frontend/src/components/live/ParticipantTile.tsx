/** 单个视频格：画面或头像块 + 声波（说话时）+ 姓名/角色/静音徽标。
 *
 * 设计事实源：docs/02-modules/r002-livekit-features.md §4.1、§4.7（专注感的四个来源）。
 * 头像块不是「占位」：无摄像头时用主题色渐变 + 首字，并在说话时给出声波脉冲——让「谁在说」可感知。
 */
import type { ReactNode } from 'react'
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
  /** 焦点/共享徽标（只有人为状态才传，见 FocusBadge 的口径）。 */
  badge?: ReactNode
  /** 覆盖显示名（离线焦点等没有 Participant 的场景）。 */
  displayNameOverride?: string
}

function initial(name: string): string {
  const trimmed = name.trim()
  return trimmed ? trimmed.slice(0, 1) : '?'
}

export default function ParticipantTile({
  participant,
  publication,
  role,
  isFocus = false,
  speaking = false,
  badge,
  displayNameOverride,
}: Props) {
  const name = displayNameOverride || participant.name || participant.identity
  const showVideo = Boolean(publication && !publication.isMuted)
  const classes = ['live-tile']
  if (isFocus) classes.push('live-tile-focus')
  if (speaking) classes.push('live-tile-speaking')

  return (
    <div className={classes.join(' ')}>
      {showVideo ? (
        <VideoTrack trackRef={{ participant, publication: publication!, source: publication!.source }} />
      ) : (
        <div className="live-avatar-wrap">
          {speaking && <span className="live-avatar-pulse" aria-hidden />}
          <span className="live-avatar" aria-hidden>
            {initial(name)}
          </span>
        </div>
      )}
      {badge}
      <div className="live-tile-bar">
        <span className="live-tile-name">{name}</span>
        {role && <span className={`chip ${role === 'host' ? 'chip-warn' : 'chip-quiet'}`}>{ROLE_LABEL[role]}</span>}
        {!showVideo && <MicOff {...ICON} aria-label="麦克风未开" />}
      </div>
    </div>
  )
}
