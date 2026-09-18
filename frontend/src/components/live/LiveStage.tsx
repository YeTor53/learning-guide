/** 舞台：单焦点布局（说话者主格 + 其余沿右侧竖排的窄缩格）。
 *
 * 设计事实源：docs/02-modules/r002-livekit-features.md §4.1、§4.7（专注感的四个来源）。
 * 专注感的三条实现：① 一个人占主格、其余降权退到边上；② 空态给出「在等谁 + 今天聊什么 + 房间码」而非纯黑；
 * ③ 说话有可见反馈（声波 / 上缘强调线），让「专注」是看得见的现场，而不是一块黑。
 */
import { Track } from 'livekit-client'
import { useTracks } from '@livekit/components-react'

import type { Member, Role, Room } from '../../api/rooms'
import ParticipantTile from './ParticipantTile'

interface Props {
  room: Room
  members: Member[]
  speakerIdentity: string | null
  localIdentity: string
}

export default function LiveStage({ room, members, speakerIdentity, localIdentity }: Props) {
  const tracks = useTracks([{ source: Track.Source.Camera, withPlaceholder: true }], { onlySubscribed: false })
  const byIdentity = new Map(members.map((member) => [member.userId, member]))

  const focusIdentity = speakerIdentity ?? localIdentity
  const focus = tracks.find((item) => item.participant.identity === focusIdentity) ?? tracks[0]
  const rail = tracks.filter((item) => item.participant.identity !== focus?.participant.identity)
  const roleOf = (identity: string): Role | null => byIdentity.get(identity)?.role ?? null

  if (tracks.length === 0) {
    return (
      <div className="live-stage live-stage-empty">
        <p className="live-empty-title">等待其他成员加入</p>
        <p className="live-empty-sub">今天的主题：{room.topicLabel}</p>
        <span className="live-empty-code mono">房间码 {room.roomCode}</span>
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
