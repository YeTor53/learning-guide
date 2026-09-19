/** hero 底缘的「向下」提示（r007；Q1=1 / Q2=2，2026-09-19 追加：**更大 + 两支**）。
 *
 * 口径：**纯装饰、不可点**（不加文字、不绑 onClick、不进 tab 序、`pointer-events: none`）；
 * 两支箭头**错峰**浮动，幅度与节奏都是令牌：
 * `--scroll-hint-size`（尺寸）/ `--scroll-hint-travel`（位移）/ `--scroll-hint-duration`（周期）/ `--scroll-hint-gap`（两支间距）。
 * `prefers-reduced-motion` 下停止浮动（最后一处 reduced-motion 块里显式关掉）。
 */
import { ChevronDown } from 'lucide-react'

export default function ScrollHint() {
  return (
    <div className="scroll-hint" role="presentation" aria-hidden>
      <ChevronDown strokeWidth={1.5} className="scroll-hint-arrow" />
      <ChevronDown strokeWidth={1.5} className="scroll-hint-arrow" />
    </div>
  )
}
