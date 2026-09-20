/** 设备状态保持（设备层）：麦克风/摄像头开关记在 React state，重连后按记忆值重放。
 *
 * 设计事实源：docs/02-modules/r002-livekit.md §8.10（含 C-3 实测项）。
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { Room, RoomEvent } from 'livekit-client'

export interface LocalDeviceState {
  micEnabled: boolean
  camEnabled: boolean
  toggleMic: () => Promise<void>
  toggleCam: () => Promise<void>
}

/**
 * @param publishDevices 是否允许发布设备（默认 true）。r012：超管的 Token 没有发布权限
 *   （`canPublish=false`），传 false 时不自动开麦/开摄像头，也不重放记忆值——避免「界面显示已开、
 *   实际上被服务端拒绝」的假状态（见 ADR-0024 D3）。
 */
export function useLocalDeviceState(room: Room, status: string, publishDevices = true): LocalDeviceState {
  const [micEnabled, setMicEnabled] = useState(publishDevices)
  const [camEnabled, setCamEnabled] = useState(false)
  const memory = useRef({ mic: publishDevices, cam: false })

  const toggleMic = useCallback(async () => {
    const next = !memory.current.mic
    memory.current.mic = next
    setMicEnabled(next)
    await room.localParticipant.setMicrophoneEnabled(next)
  }, [room])

  const toggleCam = useCallback(async () => {
    const next = !memory.current.cam
    memory.current.cam = next
    setCamEnabled(next)
    await room.localParticipant.setCameraEnabled(next)
  }, [room])

  // 首次连上：按默认值发布轨道（麦克风开、摄像头关）；超管不发布（publishDevices=false）
  useEffect(() => {
    if (!publishDevices || status !== 'connected') return
    void room.localParticipant.setMicrophoneEnabled(memory.current.mic)
    void room.localParticipant.setCameraEnabled(memory.current.cam)
  }, [room, status, publishDevices])

  // 重连成功：按记忆值重放（§8.10）
  useEffect(() => {
    if (!publishDevices) return
    const onReconnected = () => {
      void room.localParticipant.setMicrophoneEnabled(memory.current.mic)
      void room.localParticipant.setCameraEnabled(memory.current.cam)
    }
    room.on(RoomEvent.Reconnected, onReconnected)
    return () => {
      room.off(RoomEvent.Reconnected, onReconnected)
    }
  }, [room, publishDevices])

  return { micEnabled, camEnabled, toggleMic, toggleCam }
}
