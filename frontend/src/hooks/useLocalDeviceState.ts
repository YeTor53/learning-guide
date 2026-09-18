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

export function useLocalDeviceState(room: Room, status: string): LocalDeviceState {
  const [micEnabled, setMicEnabled] = useState(true)
  const [camEnabled, setCamEnabled] = useState(false)
  const memory = useRef({ mic: true, cam: false })

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

  // 首次连上：按默认值发布轨道（麦克风开、摄像头关）
  useEffect(() => {
    if (status !== 'connected') return
    void room.localParticipant.setMicrophoneEnabled(memory.current.mic)
    void room.localParticipant.setCameraEnabled(memory.current.cam)
  }, [room, status])

  // 重连成功：按记忆值重放（§8.10）
  useEffect(() => {
    const onReconnected = () => {
      void room.localParticipant.setMicrophoneEnabled(memory.current.mic)
      void room.localParticipant.setCameraEnabled(memory.current.cam)
    }
    room.on(RoomEvent.Reconnected, onReconnected)
    return () => {
      room.off(RoomEvent.Reconnected, onReconnected)
    }
  }, [room])

  return { micEnabled, camEnabled, toggleMic, toggleCam }
}
