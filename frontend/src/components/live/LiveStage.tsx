/** 舞台：单焦点布局（焦点主格 + 其余沿右侧竖排的窄缩格）。
 *
 * 焦点优先级（为 M3 屏幕共享预留，本轮不出现共享按钮）：**屏幕共享 > 说话者 > 自己**。
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
  /** 是否已连上实时服务：未连接时不渲染任何格子（否则会渲染出无名占位格）。 */
  connected: boolean
  members: Member[]
  speakerIdentity: string | null
  localIdentity: string
}

export default function LiveStage({ room, connected, members, speakerIdentity, localIdentity }: Props) {
  const tracks = useTracks(
    [{ source: Track.Source.ScreenShare, withPlaceholder: false }, { source: Track.Source.Camera, withPlaceholder: true }],
    { onlySubscribed: false },
  )
  const byIdentity = new Map(members.map((member) => [member.userId, member]))

  // 焦点优先级：屏幕共享 > 说话者 > 自己（M3 共享功能落地时无需改这里）
  const screenShare = tracks.find((item) => item.source === Track.Source.ScreenShare && !item.publication?.isMuted)
  const focusIdentity = screenShare?.participant.identity ?? speakerIdentity ?? localIdentity
  const focus = tracks.find((item) => item.participant.identity === focusIdentity && item.source !== Track.Source.ScreenShare) ?? screenShare ?? tracks[0]
  const rail = tracks.filter(
    (item) => item !== focus && item.participant.identity !== focus?.participant.identity && item.source !== Track.Source.ScreenShare,
  )
  const roleOf = (identity: string): Role | null => byIdentity.get(identity)?.role ?? null

  if (!connected || tracks.length === 0) {
    return (
      <div className="live-stage live-stage-empty">
        <p className="live-empty-title">{connected ? '等待其他成员加入' : '还没有连上实时服务'}</p>
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
