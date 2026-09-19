/** 房内 Data Channel：订阅与发布（只是「加速层」，真相在库，ADR-0013）。
 *
 * 设计事实源：docs/rounds/r004-room-extras/design.md §5.5、§6（topic 与收敛规则）
 * 约定：JSON 编码、`reliable: true`、按 topic 分发；快照类消息由调用方用 `at` 时间戳收敛。
 */
import { useEffect, useRef } from 'react'
import { Room, RoomEvent } from 'livekit-client'

export const CHANNEL_TOPIC = {
  chat: 'lg.chat',
  hands: 'lg.hands',
  focus: 'lg.focus',
  screenStop: 'lg.screen.stop',
} as const

export type ChannelTopic = (typeof CHANNEL_TOPIC)[keyof typeof CHANNEL_TOPIC]

const encoder = new TextEncoder()
const decoder = new TextDecoder()

/** 发布一条 JSON 载荷；失败只记日志（广播丢包由「重连后 refresh」兜底）。 */
export async function publishSnapshot<T>(room: Room, topic: ChannelTopic, payload: T): Promise<void> {
  try {
    await room.localParticipant.publishData(encoder.encode(JSON.stringify(payload)), { reliable: true, topic })
  } catch (error) {
    console.warn('[lg] 广播失败（不影响落库）', topic, error)
  }
}

/** 订阅某个 topic；handler 用 ref 持有，避免调用方每次渲染重订阅。 */
export function useDataChannel<T>(
  room: Room | null,
  topic: ChannelTopic,
  onMessage: (payload: T, fromIdentity: string | null) => void,
): void {
  const handlerRef = useRef(onMessage)
  handlerRef.current = onMessage

  useEffect(() => {
    if (!room) return
    const onData = (
      payload: Uint8Array,
      participant?: { identity?: string },
      _kind?: unknown,
      incomingTopic?: string,
    ) => {
      if (incomingTopic !== topic) return
      try {
        handlerRef.current(JSON.parse(decoder.decode(payload)) as T, participant?.identity ?? null)
      } catch {
        // 非法载荷直接忽略：广播只是加速层，不允许影响主流程
      }
    }
    room.on(RoomEvent.DataReceived, onData)
    return () => {
      room.off(RoomEvent.DataReceived, onData)
    }
  }, [room, topic])
}
