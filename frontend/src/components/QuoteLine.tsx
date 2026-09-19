/** 解释性文案旁的哲学语句（r006，ADR-0017 D3 扩展）。
 *
 * 口径：**不替换功能性文本**，只在「解释性 / 说明性 / 空态」文案旁补一句；
 * 同一槽位同一天稳定（刷新不变），跨天轮换；语录来自 `content/philosophy.ts` 的池子。
 */
import { useMemo } from 'react'

import { pickQuoteFor } from '../content/philosophy'

interface Props {
  /** 槽位名：决定用哪一句（同一页面不同位置给不同槽位）。 */
  slot: string
  className?: string
}

export default function QuoteLine({ slot, className }: Props) {
  const quote = useMemo(() => pickQuoteFor(slot), [slot])
  return (
    <p className={`quote-line${className ? ` ${className}` : ''}`}>
      {quote.text}
      <cite>—— {quote.author}</cite>
    </p>
  )
}
