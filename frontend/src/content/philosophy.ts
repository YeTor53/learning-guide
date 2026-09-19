/** 哲学语句池（r006，ADR-0017 D3）。
 *
 * 口径：**只收真实语录**（中文译句 + 作者），不写自造句子；这是全仓唯一来源，替换只改这一个文件。
 * 「每日一句」而非「每次随机」：同一天里多端、多次打开看到的是同一句（可复现、可截图取证），跨天才变。
 */
export interface PhilosophyQuote {
  text: string
  author: string
}

export const PHILOSOPHY_QUOTES: readonly PhilosophyQuote[] = [
  { text: '未经审视的人生，是不值得过的。', author: '苏格拉底' },
  { text: '认识你自己。', author: '德尔斐神庙箴言' },
  { text: '我思，故我在。', author: '笛卡尔' },
  { text: '人是一根会思想的苇草。', author: '帕斯卡' },
  { text: '知之为知之，不知为不知，是知也。', author: '孔子' },
  { text: '吾生也有涯，而知也无涯。', author: '庄子' },
  { text: '知行合一。', author: '王阳明' },
  { text: '当你凝视深渊时，深渊也在凝视你。', author: '尼采' },
  { text: '人是自己选择的总和。', author: '萨特' },
  { text: '在隆冬，我终于知道，我身上有一个不可战胜的夏天。', author: '加缪' },
  { text: '参差多态，乃是幸福的本源。', author: '罗素' },
  { text: '人，诗意地栖居。', author: '荷尔德林' },
] as const

/** 按「UTC+8 的年内第几天」取模选一句：同日稳定、跨天变化（纯函数，便于用例覆盖）。 */
export function pickDailyQuote(date: Date = new Date()): PhilosophyQuote {
  const beijing = new Date(date.getTime() + 8 * 60 * 60 * 1000)
  const yearStart = Date.UTC(beijing.getUTCFullYear(), 0, 1)
  const dayOfYear = Math.floor((beijing.getTime() - yearStart) / 86_400_000)
  const index = ((dayOfYear % PHILOSOPHY_QUOTES.length) + PHILOSOPHY_QUOTES.length) % PHILOSOPHY_QUOTES.length
  return PHILOSOPHY_QUOTES[index]
}

/** 槽位散列（简单确定性散列：同一个槽位永远落在同一组起始下标上）。 */
function hashSlot(slot: string): number {
  let hash = 0
  for (let i = 0; i < slot.length; i += 1) {
    hash = (hash * 31 + slot.charCodeAt(i)) % 100_000
  }
  return hash
}

/**
 * 给某个「文案槽位」挑一句：同一槽位**同一天**稳定（刷新不变），不同槽位尽量不撞，跨天轮换。
 * 用法：`pickQuoteFor('home-hero')` / `pickQuoteFor('chat-empty')`。
 */
export function pickQuoteFor(slot: string, date: Date = new Date()): PhilosophyQuote {
  const beijing = new Date(date.getTime() + 8 * 60 * 60 * 1000)
  const yearStart = Date.UTC(beijing.getUTCFullYear(), 0, 1)
  const dayOfYear = Math.floor((beijing.getTime() - yearStart) / 86_400_000)
  const index = (hashSlot(slot) + dayOfYear) % PHILOSOPHY_QUOTES.length
  return PHILOSOPHY_QUOTES[index]
}
