/** 舞台：**均分铺满**（r009）。谁在哪、多大由 `computeStageGeometry` 纯函数决定；位置变化由 FLIP 播放。
 *
 * 设计事实源：docs/rounds/r009-focus-system/{design.md §1, motion-design.md}；焦点优先级沿用 ADR-0014
 * （共享 > 手动焦点 > 说话者 > 自己），r009 只改「布局形态」与「动效表达」。
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Track } from 'livekit-client'
import type { Participant, TrackPublication } from 'livekit-client'
import { useTracks } from '@livekit/components-react'

import type { Member, Role, Room } from '../../api/rooms'
import { useFlipTransition, useLeavingIds } from '../../hooks/useFlipTransition'
import FocusBadge from './FocusBadge'
import QuoteLine from '../QuoteLine'
import ParticipantTile from './ParticipantTile'
import { isAgentParticipant } from '../../hooks/useOnlineIdentities'
import { computeStageGeometry } from './stageGeometry'

interface Props {
  room: Room
  connected: boolean
  members: Member[]
  onlineIds: string[]
  speakerIdentity: string | null
  localIdentity: string
  focusUserId: string | null
  screenOwnerId: string | null
  micStates: Record<string, boolean>
  sharing: boolean
  onStopShare: () => void
  /** r009：正在举手的人（举手格持续闪烁，纯视觉、不参与几何）。 */
  handIds?: string[]
  /** r009：我是否有管理权限（举手格上显示「给焦点 / 放下手」角标）。 */
  canGrant?: boolean
  onGrantFocus?: (identity: string) => void
  onLowerHand?: (identity: string) => void
}

/** callback ref 包装：节点出现/替换都触发一次 state 更新（见 useStageArea 注释）。 */
function useCallbackRef(setter: (node: HTMLDivElement | null) => void) {
  return useCallback((node: HTMLDivElement | null) => setter(node), [setter])
}

interface TrackRef {
  participant: Participant
  publication: TrackPublication | undefined
  isScreen: boolean
}

/**
 * 区域尺寸：ResizeObserver + 150ms 去抖（motion-design C7，拖窗口时不逐帧重排）。
 *
 * 用 **callback ref + state** 而不是 `useRef`：舞台在「空态」与「网格」两个分支里是**不同节点**，
 * `useRef` 对象的引用又永远稳定 → 从空态切到网格时 effect 不会重跑、observer 从未建立、尺寸恒为 0
 * （cp-1b 实测踩到：格子全不渲染）。callback ref 在节点出现/替换时都会更新，effect 才能重建。
 */
function useStageArea(node: HTMLDivElement | null) {
  const [area, setArea] = useState({ w: 0, h: 0 })
  useEffect(() => {
    if (!node) return
    let timer = 0
    const measure = () => {
      const rect = node.getBoundingClientRect()
      const pad = 12 * 2 // --stage-pad 上下左右各一次（几何按内容区算）
      setArea({ w: Math.max(0, rect.width - pad), h: Math.max(0, rect.height - pad) })
    }
    measure()
    const observer = new ResizeObserver(() => {
      window.clearTimeout(timer)
      timer = window.setTimeout(measure, 150)
    })
    observer.observe(node)
    return () => {
      window.clearTimeout(timer)
      observer.disconnect()
    }
  }, [node])
  return area
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
  micStates,
  sharing,
  onStopShare,
  handIds = [],
  canGrant = false,
  onGrantFocus,
  onLowerHand,
}: Props) {
  const rawTracks = useTracks(
    [{ source: Track.Source.ScreenShare, withPlaceholder: false }, { source: Track.Source.Camera, withPlaceholder: true }],
    { onlySubscribed: false },
  )
  // r010：房间里的 agent（转写 worker）也是 LiveKit 参与者，但**不是房间成员**——
  // `withPlaceholder: true` 会给每个没有摄像头的人发占位轨，agent 因此会在舞台上多占一格（实测踩到）。
  // 这里统一剔除：舞台只渲染人。
  const tracks = useMemo(() => rawTracks.filter((item) => !isAgentParticipant(item.participant)), [rawTracks])
  const [stageEl, setStageEl] = useState<HTMLDivElement | null>(null)
  const stageRef = useCallbackRef(setStageEl)
  const area = useStageArea(stageEl)

  const byIdentity = useMemo(() => new Map(members.map((member) => [member.userId, member])), [members])
  const micMutedOf = (participant: Participant) => !(micStates[participant.identity] ?? participant.isMicrophoneEnabled)
  const focusMemberActive = Boolean(
    focusUserId && members.some((member) => member.userId === focusUserId && member.status === 'active'),
  )
  // r011（你 2026-09-20 口径）：**说话不再获得焦点** —— 焦点只来自「屏幕共享」或
  // 「房主/协管手动指定（含举手→给焦点）」；说话只保留视觉高亮（声波/描边），不再改布局。
  // 原 C4 的说话者自动焦点（去抖/冷却/保护期）整体废止，见
  // `docs/rounds/r011-debt-backfill/redirect-02.md` 与 ADR-0014 的变更记录。

  /** identity → 首选轨道：共享中的那个人取屏幕共享轨，其余取摄像头/占位轨。 */
  const trackOf = useMemo(() => {
    const map = new Map<string, TrackRef>()
    for (const item of tracks) {
      const identity = item.participant.identity
      const isScreen = item.source === Track.Source.ScreenShare && !item.publication?.isMuted
      const existing = map.get(identity)
      const next: TrackRef = { participant: item.participant, publication: item.publication, isScreen }
      if (!existing) map.set(identity, next)
      else if (isScreen && identity === screenOwnerId) map.set(identity, next)
    }
    return map
  }, [tracks, screenOwnerId])

  // 稳定排序（motion-design C8）：本地 → 焦点 → 其余按在线顺序；避免每次重排大洗牌
  const ordered = useMemo(() => {
    const ids = Array.from(trackOf.keys())
    const focusId = screenOwnerId ?? (focusMemberActive ? focusUserId : null)
    const rank = (identity: string) => {
      if (identity === localIdentity) return 0
      if (focusId && identity === focusId) return 1
      return 2
    }
    return ids.slice().sort((a, b) => {
      const diff = rank(a) - rank(b)
      if (diff !== 0) return diff
      return onlineIds.indexOf(a) - onlineIds.indexOf(b)
    })
  }, [trackOf, localIdentity, focusMemberActive, focusUserId, screenOwnerId, onlineIds])

  const geometry = useMemo(() => {
    const focusIdentity = screenOwnerId ?? (focusMemberActive ? focusUserId : null)
    return computeStageGeometry({
      areaW: area.w,
      areaH: area.h,
      identities: ordered,
      focusIdentity: screenOwnerId ? null : focusIdentity,
      shareIdentity: screenOwnerId,
    })
  }, [area.w, area.h, ordered, screenOwnerId, focusMemberActive, focusUserId])

  const shownIds = useLeavingIds(geometry.tiles.map((tile) => tile.identity))
  const placedIds = new Set(geometry.tiles.map((tile) => tile.identity))
  const layoutKey = `${area.w}x${area.h}|${shownIds.join(',')}|${geometry.mode}|${geometry.focusIdentity ?? '-'}`
  useFlipTransition(stageEl, { layoutKey })

  if (!connected || tracks.length === 0) {
    return (
      <div className="live-stage live-stage-empty">
        <p className="live-empty-title">{connected ? '等待其他成员加入' : '还没有连上实时服务'}</p>
        <p className="live-empty-sub">今天的主题：{room.topicLabel}</p>
        <QuoteLine scene="meet" />
        <span className="live-empty-code mono">房间码 {room.roomCode}</span>
      </div>
    )
  }

  const roleOf = (identity: string): Role | null => byIdentity.get(identity)?.role ?? null
  const nameOf = (identity: string): string => byIdentity.get(identity)?.displayName ?? identity

  return (
    <div
      className="live-stage live-stage-grid"
      ref={stageRef}
      data-stage-mode={geometry.mode}
      data-stage-area={`${Math.round(area.w)}x${Math.round(area.h)}`}
      data-stage-ids={ordered.join(' ')}
    >
      {shownIds.map((identity) => {
        const tile = geometry.tiles.find((candidate) => candidate.identity === identity)
        const leaving = !placedIds.has(identity)
        const track = trackOf.get(identity)
        const rect = tile ?? { x: 0, y: 0, w: 0, h: 0 }
        const isFocus = Boolean(tile && tile.kind === 'focus')
        const isSelf = identity === localIdentity
        return (
          <div
            key={identity}
            data-flip-id={identity}
            data-kind={tile?.kind ?? 'leaving'}
            className={`live-cell${leaving ? ' is-leaving' : ''}${isFocus ? ' is-focus' : ''}${tile?.kind === 'share' ? ' is-share' : ''}${handIds.includes(identity) ? ' is-hand' : ''}`}
            style={{ left: rect.x, top: rect.y, width: rect.w, height: rect.h }}
          >
            {isSelf && !leaving && <span className="live-cell-self">（你）</span>}
            {/* r009：举手者格上的管理动作（给焦点 / 放下手）——只在管理身份且对方未处于焦点时出现 */}
            {canGrant && !leaving && track && handIds.includes(identity) && !isFocus && (
              <span className="live-cell-hand-actions">
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={() => onGrantFocus?.(identity)}
                >
                  给焦点
                </button>
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => onLowerHand?.(identity)}>
                  放下手
                </button>
              </span>
            )}
            {track && !leaving ? (
              <ParticipantTile
                participant={track.participant}
                publication={track.publication}
                role={roleOf(identity)}
                isFocus={isFocus}
                speaking={identity === speakerIdentity}
                micMuted={micMutedOf(track.participant)}
                badge={
                  isFocus && geometry.focusIdentity === identity && tile?.kind !== 'share' ? (
                    <FocusBadge kind="focus" name={nameOf(identity)} isSelf={isSelf} />
                  ) : null
                }
              />
            ) : (
              <div className={`live-tile${isFocus ? ' live-tile-focus' : ''} live-tile-placeholder`}>
                <div className="live-avatar-wrap">
                  <span className="live-avatar" aria-hidden>
                    {nameOf(identity).slice(0, 1)}
                  </span>
                </div>
                {isFocus && <FocusBadge kind="focus" name={nameOf(identity)} isSelf={isSelf} />}
                <div className="live-tile-bar">
                  <span className="live-tile-name">{nameOf(identity)}</span>
                  {leaving && <span className="chip chip-quiet">已离开</span>}
                </div>
              </div>
            )}
          </div>
        )
      })}

      {sharing && (
        <button className="btn btn-sm live-share-stop" onClick={onStopShare}>
          停止共享
        </button>
      )}
    </div>
  )
}
