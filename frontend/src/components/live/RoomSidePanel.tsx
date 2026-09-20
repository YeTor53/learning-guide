/** 管理抽屉（默认收起）：**活跃 / 非活跃**成员 + 待批申请 + 房间码。
 *
 * 设计事实源：docs/02-modules/r002-livekit-features.md §3 F-16、§4.2（按钮矩阵）、§4.6（按钮决策表）、§4.9（与管理页分工）。
 * 口径（用户 2026-09-18 定）：成员按**在不在房间内**分两类——
 *   - 活跃（在房间里）= 此刻连着房间（LiveKit 在场，ADR-0011 条 1 的"瞬时事实源"）；
 *   - 非活跃（不在房间内）= 此刻不在房间里（离线，或已离开 / 被移出 / 房间结束）。
 * 注意与库里的 `room_members.status` 区分：那是"成员身份是否有效"，不是"此刻在不在"。
 */
import { useState } from 'react'
import { Check, Copy, Crosshair, Hand, MoreHorizontal, ShieldCheck, ShieldOff, UserMinus, X } from 'lucide-react'

import JoinRequestList from '../JoinRequestList'
import type { JoinRequest, Member, Room, Role, ViewerRole } from '../../api/rooms'
import { EXIT_REASON_LABEL, ROLE_LABEL } from '../../api/rooms'
import type { ChatState } from '../../hooks/useChatMessages'
import type { SpeechLine } from '../../hooks/useTranscription'
import type { FocusState } from '../../hooks/useRoomFocus'
import type { HandState } from '../../hooks/useHandRaise'
import type { ScreenShareState } from '../../hooks/useScreenShare'
import ChatPanel from './ChatPanel'
import InvitePanel from './InvitePanel'

const ICON = { size: 14, strokeWidth: 1.75 } as const

interface Props {
  /** r009：协管焦点申请（待批 + 批准/拒绝）。 */
  focusRequests?: {
    requests: import('../../hooks/useFocusRequests').FocusRequest[]
    mine: import('../../hooks/useFocusRequests').FocusRequest | null
    approve: (id: string) => Promise<void>
    reject: (id: string) => Promise<void>
  }

  room: Room
  members: Member[]
  myRole: ViewerRole | null
  onlineIds: string[]
  requests: JoinRequest[]
  busyId: string | null
  /** r004：讨论（群聊）状态与我的 user id。 */
  chat: ChatState
  myUserId: string | null
  /** r010：语音转写（定稿 + 渐进），透传给讨论面板。 */
  speech?: SpeechLine[]
  live?: SpeechLine[]
  /** r004：举手 / 焦点 / 共享。 */
  hands: HandState
  focus: FocusState
  screen: ScreenShareState
  /** 未读数清零（抽屉打开且消息变化时由页面调用）。 */
  onChatChanged: () => void
  onClose: () => void
  onKick: (userId: string) => void
  onSetRole: (userId: string, role: Exclude<Role, 'host'>) => void
  onTransferHost: (userId: string) => void
  onApprove: (requestId: string) => void
  onReject: (requestId: string) => void
}

/** 副行只讲「为什么不在」：仍是成员但离线 → 不写（chip 已经说了不在房间）；已不是成员 → 写原因。 */
function inactiveReason(member: Member): string | null {
  if (member.status !== 'inactive') return null
  return member.exitReason ? `${EXIT_REASON_LABEL[member.exitReason]} · 已不是成员` : '已不是成员'
}

export default function RoomSidePanel({
  room,
  members,
  myRole,
  onlineIds,
  requests,
  busyId,
  chat,
  myUserId,
  speech = [],
  live = [],
  hands,
  focus,
  screen,
  onChatChanged,
  onClose,
  onKick,
  onSetRole,
  onTransferHost,
  onApprove,
  onReject,
  focusRequests,
}: Props) {
  const isHost = myRole === 'host'
  const isManager = myRole === 'host' || myRole === 'moderator'
  const online = new Set(onlineIds)
  /** r004：抽屉双 tab —— 「讨论」默认（U1），「成员」放原治理内容。 */
  const [tab, setTab] = useState<'chat' | 'members' | 'invite'>('chat')
  const myHands = hands.hands.filter((item) => item.userId !== myUserId)
  const [openMenuId, setOpenMenuId] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const activeMembers = members.filter((member) => online.has(member.userId))
  const inactiveMembers = members.filter((member) => !online.has(member.userId))

  const copyCode = async () => {
    try {
      await navigator.clipboard.writeText(room.roomCode)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopied(false)
    }
  }

  const renderRow = (member: Member, active: boolean) => (
    <div className={`member-row${active ? '' : ' member-row-quiet'}`} key={member.id}>
      <div style={{ minWidth: 0 }}>
        <div className="member-name">
          {member.displayName}
          <span className={`chip ${member.role === 'host' ? 'chip-warn' : 'chip-quiet'}`}>{ROLE_LABEL[member.role]}</span>
          <span className={`chip ${active ? 'chip-accent' : 'chip-quiet'}`}>{active ? '在房间里' : '不在房间'}</span>
        </div>
        {!active && inactiveReason(member) && (
          <span className="dim mono" style={{ fontSize: 11 }}>{inactiveReason(member)}</span>
        )}
      </div>
      {isManager && member.userId !== room.hostId && (
        <div className="member-actions">
          <button
            className="btn btn-ghost btn-sm"
            disabled={busyId === member.userId}
            onClick={() => onKick(member.userId)}
            title={`把 ${member.displayName} 移出房间`}
          >
            <UserMinus {...ICON} />
            移出
          </button>
          {isHost && (
            <button
              className="btn btn-ghost btn-sm"
              disabled={busyId === member.userId}
              onClick={() => onSetRole(member.userId, member.role === 'moderator' ? 'participant' : 'moderator')}
              title={member.role === 'moderator' ? `取消 ${member.displayName} 的协管` : `把 ${member.displayName} 设为协管`}
            >
              {member.role === 'moderator' ? <ShieldOff {...ICON} /> : <ShieldCheck {...ICON} />}
              {member.role === 'moderator' ? '取消协管' : '设为协管'}
            </button>
          )}
          {isManager && member.status === 'active' && (
            <button
              className={`btn btn-sm ${focus.focus.subjectUserId === member.userId ? 'btn-accent' : 'btn-ghost'}`}
              disabled={busyId === member.userId}
              onClick={() => void focus.setFocus(focus.focus.subjectUserId === member.userId ? null : member.userId)}
              title={
                focus.focus.subjectUserId === member.userId
                  ? `取消 ${member.displayName} 的焦点`
                  : `把发言焦点给 ${member.displayName}（两端的焦点格都会切到他）`
              }
            >
              <Crosshair {...ICON} />
              {focus.focus.subjectUserId === member.userId ? '取消焦点' : '给焦点'}
            </button>
          )}
          {isManager && screen.ownerId === member.userId && (
            <button
              className="btn btn-ghost btn-sm"
              disabled={busyId === member.userId}
              onClick={() => void screen.requestStop(member.userId)}
              title={`请求 ${member.displayName} 停止共享（协作式：对方客户端会自己停）`}
            >
              请求停止共享
            </button>
          )}
          {isHost && (
            <div className="more-menu">
              <button
                className="icon-btn"
                aria-haspopup="menu"
                aria-expanded={openMenuId === member.userId}
                title="更多"
                onClick={() => setOpenMenuId(openMenuId === member.userId ? null : member.userId)}
              >
                <MoreHorizontal {...ICON} />
              </button>
              {openMenuId === member.userId && (
                <div className="more-menu-pop" role="menu">
                  <button
                    role="menuitem"
                    onClick={() => {
                      setOpenMenuId(null)
                      onTransferHost(member.userId)
                    }}
                  >
                    移交房主给 {member.displayName}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )

  return (
    <aside className="live-drawer">
      <div className="live-drawer-head">
        <div className="live-drawer-tabs" role="tablist" aria-label="抽屉分区">
          <button
            role="tab"
            aria-selected={tab === 'chat'}
            className={`live-drawer-tab${tab === 'chat' ? ' on' : ''}`}
            onClick={() => setTab('chat')}
          >
            讨论
          </button>
          <button
            role="tab"
            aria-selected={tab === 'members'}
            className={`live-drawer-tab${tab === 'members' ? ' on' : ''}`}
            onClick={() => setTab('members')}
          >
            成员
            {requests.filter((item) => item.status === 'pending').length > 0 && (
              <span className="live-toggle-badge">{requests.filter((item) => item.status === 'pending').length}</span>
            )}
          </button>
          {(room.myRole === 'host' || room.myRole === 'moderator') && (
            <button
              role="tab"
              aria-selected={tab === 'invite'}
              className={`live-drawer-tab${tab === 'invite' ? ' on' : ''}`}
              onClick={() => setTab('invite')}
            >
              邀请
            </button>
          )}
        </div>
        <button className="icon-btn" onClick={onClose} title="收起（Esc）" aria-label="收起成员与管理">
          <X {...ICON} />
        </button>
      </div>

      {tab === 'members' && focusRequests && focusRequests.requests.length > 0 && (
        <section className="panel focus-requests">
          <h2 className="panel-title">焦点申请</h2>
          {focusRequests.requests.map((item) => {
            const isMine = focusRequests.mine?.id === item.id
            return (
              <div key={item.id} className="focus-request-row">
                <span className="focus-request-name">{item.requesterName}</span>
                <span className="muted" style={{ fontSize: 12 }}>申请取得焦点</span>
                {isMine ? (
                  <span className="dim" style={{ fontSize: 12 }}>需另一位管理身份批准</span>
                ) : (
                  <span className="focus-request-actions">
                    <button
                      className="btn btn-primary btn-sm"
                      onClick={() => {
                        void focusRequests.approve(item.id)
                        // 批准后由**批准人**的客户端补一次焦点广播，保证全场（尤其申请人）立刻看到焦点变化
                        void focus.setFocus(item.requesterId)
                      }}
                    >
                      批准
                    </button>
                    <button className="btn btn-ghost btn-sm" onClick={() => void focusRequests.reject(item.id)}>
                      拒绝
                    </button>
                  </span>
                )}
              </div>
            )
          })}
        </section>
      )}

      {tab === 'chat' && (
        <section className="panel">
          {myHands.length > 0 && (
            <div className="hand-strip" role="status">
              <Hand size={14} strokeWidth={1.75} />
              正在举手：{myHands.map((item) => item.displayName).join('、')}
              {isManager && (
                <button className="btn btn-ghost btn-sm" onClick={() => void hands.lowerOther(myHands[0].userId)}>
                  放下 {myHands[0].displayName}
                </button>
              )}
            </div>
          )}
          <ChatPanel chat={chat} myUserId={myUserId} onChanged={onChatChanged} speech={speech} live={live} />
        </section>
      )}

      {tab === 'members' && (
      <>

      <section className="panel">
        <h2 className="panel-title">
          活跃（在房间里）· {activeMembers.length}
          <span className="dim" style={{ fontSize: 12, fontWeight: 400, marginLeft: 8 }}>
            上限 {room.capacity} 人
          </span>
        </h2>
        {activeMembers.length === 0 ? (
          <p className="muted" style={{ fontSize: 13, margin: 0 }}>此刻没有人在房间里</p>
        ) : (
          activeMembers.map((member) => renderRow(member, true))
        )}
      </section>

      <section className="panel">
        <h2 className="panel-title">
          非活跃（不在房间内）· {inactiveMembers.length}
          <span className="dim" style={{ fontSize: 12, fontWeight: 400, marginLeft: 8 }}>
            成员共 {members.length} 人
          </span>
        </h2>
        {inactiveMembers.length === 0 ? (
          <p className="muted" style={{ fontSize: 13, margin: 0 }}>全部成员都在房间里</p>
        ) : (
          inactiveMembers.map((member) => renderRow(member, false))
        )}
      </section>

      {isManager && (
        <section className="panel">
          <h2 className="panel-title">
            待处理申请 · {requests.filter((item) => item.status === 'pending').length}
          </h2>
          <JoinRequestList requests={requests} busyId={busyId} onApprove={onApprove} onReject={onReject} pendingOnly />
        </section>
      )}

      {/* 只留「讨论中要用到」的东西：房间码（口头传播）。主题/简介/时间等归房间管理页（§4.9）。 */}
      <div className="live-code-row">
        <span className="dim mono" style={{ fontSize: 12 }}>房间码 {room.roomCode}</span>
        <button className="btn btn-ghost btn-sm" onClick={() => void copyCode()} title="复制房间码">
          {copied ? <Check {...ICON} /> : <Copy {...ICON} />}
          {copied ? '已复制' : '复制'}
        </button>
      </div>
      </>
      )}
          {tab === 'invite' && <InvitePanel roomId={room.id} />}

</aside>
  )
}
