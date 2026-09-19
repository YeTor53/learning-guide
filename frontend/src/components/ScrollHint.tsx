/** hero 底缘的「向下」提示（r007，Q1=1 / Q2=2）。
 *
 * 口径：**纯装饰、不可点**（不加文字、不绑 onClick、不进 tab 序、`pointer-events: none`）；
 * 轻浮动提示「下面还有房间列表」；`prefers-reduced-motion` 下停止浮动。
 * 形态与幅度都是令牌：`--scroll-hint-bottom` / `--scroll-hint-travel` / `--scroll-hint-duration`。
 */
import { ChevronDown } from 'lucide-react'

export default function ScrollHint() {
  return (
    <div className="scroll-hint" role="presentation" aria-hidden>
      <ChevronDown size={22} strokeWidth={1.5} />
    </div>
  )
}
