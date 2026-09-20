/** 转写与三源合一（r010）。设计事实源：`docs/rounds/r010-transcription/design.md` §9.3/§9.4；决定见 ADR-0023。
 *
 * 口径：识别在房间侧（Agents worker）→ 前端只做「监听渲染 + 把最终稿回传落库」；中间稿不落库。
 */
import { request } from './http'

export type SttMode = 'agent' | 'backend' | 'off'

export interface SttStatus {
  mode: SttMode
  agentName: string
  maxSessions: number
  segmentSeconds: number
  /** r011：全局最近一次 worker 心跳（无则 null）。 */
  lastHeartbeatAt?: string | null
  lastHeartbeatRoomId?: string | null
}

/** r011：按房的转写状态（含该房 worker 心跳，用于「转写：开启/未开启」与最后活动时间）。 */
export interface RoomSttStatus {
  mode: SttMode
  agentName: string
  maxSessions: number
  lastHeartbeatAt: string | null
  heartbeatAgeSeconds: number | null
  fresh: boolean
  workerId: string | null
  sessions: number
}

/** 三源合一的条目（聊天 / 系统事件 / 语音转写）。 */
export interface ConversationItem {
  id: string
  kind: 'chat' | 'system' | 'speech'
  at: string
  speakerId: string | null
  speakerName: string | null
  text: string
  meta: { durationMs?: number; language?: string; externalId?: string }
}

export interface SegmentIn {
  externalId: string
  speakerIdentity: string
  text: string
  startedAt: string
  durationMs: number
  language: string
  final: boolean
}

export const CONVERSATION_LIMIT = 200

export const transcriptsApi = {
  /** 转写配置状态（用于控制坞显示「转写：开启/未开启」，不报错、不伪装）。 */
  sttStatus: () => request<SttStatus>('/api/stt/status'),
  /** 按房的转写状态（r011）：控制坞取「本房 worker 最后心跳」，worker 崩了也能翻成未开启。 */
  roomSttStatus: (roomId: string) => request<RoomSttStatus>(`/api/rooms/${roomId}/stt-status`),
  /** 三源合一对话流（刷新/重进后仍能看到说过的话）。 */
  conversation: (roomId: string, limit = CONVERSATION_LIMIT) =>
    request<{ items: ConversationItem[] }>(`/api/rooms/${roomId}/conversation?limit=${limit}`),
  /** 回传一段**最终稿**（同一 externalId 重复上报幂等，服务端只落一行）。 */
  postSegment: (roomId: string, body: SegmentIn) =>
    request<{ transcript: unknown; created: boolean }>(`/api/rooms/${roomId}/transcripts/segments`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
}
