/** 舞台：单焦点布局（焦点主格 + 缩格条），全部尺寸与顺序由 `computeStageLayout` 派生。
 *
 * 设计事实源：docs/rounds/r004-room-extras/design.md §7（焦点优先级 / 尺寸阶梯 / 变换清单）、§8.2~§8.3（材质与徽标）。
 * 专注感的三条实现（r002 起）：① 一个人占主格、其余降权退到边上；② 空态给出「在等谁 + 今天聊什么 + 房间码」；
 * ③ 说话有可见反馈。**r004 起**：焦点可以来自共享或房主指定（ADR-0014），且「谁被放大」只在这里判一次。
 */
import { useEffect, useState } from 'react'
import { Track } from 'livekit-client'
import type { Participant } from 'livekit-client'
import { useTracks } from '@livekit/components-react'

import type { Member, Role, Room } from '../../api/rooms'
import FocusBadge from './FocusBadge'
import ParticipantTile from './ParticipantTile'
import { computeStageLayout } from './stageLayout'

interface Props {
  room: Room
  /** 是否已连上实时服务：未连接时不渲染任何格子（否则会渲染出无名占位格）。 */
  connected: boolean
  members: Member[]
  onlineIds: string[]
  speakerIdentity: string | null
  localIdentity: string
  /** 服务端同步的手动焦点（ADR-0014）。 */
  focusUserId: string | null
  /** 正在共享屏幕的人。 */
  screenOwnerId: string | null
  /** r006（ADR-0017 D1）：`identity → isMicrophoneEnabled`（空表时按 participant 状态兜底）。 */
  micStates: Record<string, boolean>
  sharing: boolean
  onStopShare: () => void
}

/** 视口尺寸（布局阶梯的输入之一）；窗口变化时重算。 */
function useViewport() {
  const [size, setSize] = useState(() => ({ w: window.innerWidth, h: window.innerHeight }))
  useEffect(() => {
    const onResize = () => setSize({ w: window.innerWidth, h: window.innerHeight })
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])
  return size
}

export default function LiveStage({
  room,
  connected,
  members,
  onlineIds,
  speakerIdentity,
  localIdentity,
  focusUserId,
  screenOwnerId,
  sharing,
  onStopShare,
  micStates,
}: Props) {
  const tracks = useTracks(
    [{ source: Track.Source.ScreenShare, withPlaceholder: false }, { source: Track.Source.Camera, withPlaceholder: true }],
    { onlySubscribed: false },
  )
  const viewport = useViewport()
  // 表里存的是 `isMicrophoneEnabled`（开麦=true），prop 要的是「是否静音」→ 这里取反
  const micMutedOf = (participant: Participant): boolean =>
    !(micStates[participant.identity] ?? participant.isMicrophoneEnabled)
  const byIdentity = new Map(members.map((member) => [member.userId, member]))
  const focusMemberActive = Boolean(
    focusUserId && members.some((member) => member.userId === focusUserId && member.status === 'active'),
  )

  const layout = computeStageLayout({
    online: onlineIds,
    selfIdentity: localIdentity,
    focusUserId,
    focusActive: focusMemberActive,
    shareIdentity: screenOwnerId,
    speakerIdentity,
    viewport,
  })

  if (!connected || tracks.length === 0) {
    return (
      <div className="live-stage live-stage-empty">
        <p className="live-empty-title">{connected ? '等待其他成员加入' : '还没有连上实时服务'}</p>
        <p className="live-empty-sub">今天的主题：{room.topicLabel}</p>
        <span className="live-empty-code mono">房间码 {room.roomCode}</span>
      </div>
    )
  }

  const roleOf = (identity: string): Role | null => byIdentity.get(identity)?.role ?? null
  const nameOf = (identity: string): string => byIdentity.get(identity)?.displayName ?? identity
  const focusIdentity = layout.focus?.identity ?? null
  const focusTrack = focusIdentity
    ? (tracks.find(
        (item) =>
          item.participant.identity === focusIdentity &&
          item.source === Track.Source.ScreenShare &&
          !item.publication?.isMuted,
      ) ??
      tracks.find((item) => item.participant.identity === focusIdentity) ??
      null)
    : null
  const railTracks = layout.rail
    .map((item) => ({ ...item, track: tracks.find((candidate) => candidate.participant.identity === item.identity) }))
    .filter((item): item is { identity: string; speaking: boolean; track: NonNullable<typeof item.track> } => Boolean(item.track))

  const stageClass = `live-stage${layout.railMode === 'strip' ? ' live-stage-strip' : ''}`
  const railClass = `live-rail live-rail-${layout.railMode}`

  return (
    <div className={stageClass} style={{ ['--focus-max-w' as string]: `${Math.round(layout.metrics.focusMaxWidth)}px` }}>
      {focusIdentity && (
        <div className="live-focus-slot">
          {focusTrack ? (
            <ParticipantTile
              participant={focusTrack.participant}
              publication={focusTrack.publication}
              role={roleOf(focusIdentity)}
              isFocus
              speaking={focusIdentity === speakerIdentity}

              micMuted={micMutedOf(focusTrack.participant)}
              badge={
                layout.focus && layout.focus.kind !== 'speaker' && layout.focus.kind !== 'self' ? (
                  <FocusBadge
                    kind={layout.focus.kind === 'share' ? 'share' : 'focus'}
                    name={nameOf(focusIdentity)}
                    isSelf={focusIdentity === localIdentity}
                  />
                ) : null
              }
            />
          ) : (
            /* 焦点人在册但此刻离线：显示头像块占位（§8.7 边界态：保留焦点） */
            <div className="live-tile live-tile-focus live-tile-placeholder">
              <div className="live-avatar-wrap">
                <span className="live-avatar" aria-hidden>
                  {nameOf(focusIdentity).slice(0, 1)}
                </span>
              </div>
              {layout.focus?.kind === 'focus' && (
                <FocusBadge kind="focus" name={nameOf(focusIdentity)} isSelf={focusIdentity === localIdentity} />
              )}
              <div className="live-tile-bar">
                <span className="live-tile-name">{nameOf(focusIdentity)}</span>
                <span className="chip chip-quiet">离线</span>
              </div>
            </div>
          )}
        </div>
      )}

      {railTracks.length > 0 && (
        <div className={railClass}>
          {railTracks.map((item) => (
            <ParticipantTile
              key={item.identity}
              participant={item.track.participant}
              publication={item.track.publication}
              role={roleOf(item.identity)}
              speaking={item.speaking}

              micMuted={micMutedOf(item.track.participant)}
            />
          ))}
        </div>
      )}

      {sharing && (
        <button className="btn btn-sm live-share-self" onClick={onStopShare}>
          停止共享
        </button>
      )}
    </div>
  )
}
