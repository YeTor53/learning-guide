/** 全服大屏的**右侧抽屉壳**（r012；r013 cp-6 把面板本体拆到 `GlobalChatPanel`）。
 *
 * 交互：顶栏开合按钮 → 从右侧滑入；Esc 收起；未登录只读（由面板处理）。
 * 样式参数集中在 `global.css` 的 r012 参数区（`--gc-w` 等），组件里不写死尺寸与颜色。
 * 交流页不渲染本壳（入口改为右抽屉的第四个 tab，见 `RoomSidePanel`）。
 */
import { useEffect } from 'react'

import GlobalChatPanel from './GlobalChatPanel'

interface Props {
  open: boolean
  onClose: () => void
}

export default function GlobalChatDrawer({ open, onClose }: Props) {
  // Esc 收起（与既有抽屉一致：永远有退路）
  useEffect(() => {
    if (!open) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  return (
    <aside className={`gc-drawer${open ? ' on' : ''}`} aria-hidden={!open} aria-label="全服大屏聊天">
      <GlobalChatPanel variant="drawer" enabled={open} onClose={onClose} />
    </aside>
  )
}
