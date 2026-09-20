/** 解释性文案位置的名言（r006，ADR-0017 D3 / redirect-02 批复）。
 *
 * 口径：
 * - **替换**原来的引导性解释文字（引导改由视觉与操作入口承担），保留状态事实与功能文案；
 * - 每个槽位映射到一个**场景**（`QuoteLine` 的 `scene`），从该场景的标签组里**随机**取一句 ——
 *   每次进入页面都可能换一句（同日不保证同一句，这是本轮口径）；
 * - 只写「句子 + 作者」，不写出处。
 */
import { useState } from 'react'

import { pickQuote, type QuoteScene } from '../content/philosophy'

interface Props {
  /** 场景：决定从哪一组名言里取（见 `content/philosophy.ts` 的 `QUOTE_SCENES`）。 */
  scene: QuoteScene
  className?: string
}

export default function QuoteLine({ scene, className }: Props) {
  // 挂载时随机取一次：组件不重挂载则保持不变，重新进入页面即换新
  const [quote] = useState(() => pickQuote(scene))
  return (
    <p className={`quote-line${className ? ` ${className}` : ''}`}>
      {quote.text}
      <cite>—— {quote.author}</cite>
    </p>
  )
}
