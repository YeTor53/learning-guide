/** 名言池与选句（r006，ADR-0017 D3 / redirect-02 的批复）。
 *
 * 口径（用户 2026-09-19 定）：
 * - **只收真实名言**：哲学、诗词、科学皆可，中文译句 + 作者（不写出处、不编造）；
 * - **分组打标签**（`tag`）：求知 / 科学 / 耐心 / 相遇 / 自省 / 诗意 / 告别；
 * - **场景化选句**：每个文案槽位映射到一组标签，从组里**随机**取一句（每次进入页面换新）；
 * - 这是全仓唯一来源，替换只改这一个文件。
 */
export type QuoteTag = '求知' | '科学' | '耐心' | '相遇' | '自省' | '诗意' | '告别'

export interface PhilosophyQuote {
  text: string
  author: string
  tag: QuoteTag
}

export const PHILOSOPHY_QUOTES: readonly PhilosophyQuote[] = [
  // —— 求知 ——
  { text: '我唯一知道的，就是我一无所知。', author: '苏格拉底', tag: '求知' },
  { text: '知之为知之，不知为不知，是知也。', author: '孔子', tag: '求知' },
  { text: '学而不思则罔，思而不学则殆。', author: '孔子', tag: '求知' },
  { text: '吾生也有涯，而知也无涯。', author: '庄子', tag: '求知' },
  { text: '提出一个问题往往比解决一个问题更重要。', author: '爱因斯坦', tag: '求知' },
  { text: '重要的不是停止提问。', author: '爱因斯坦', tag: '求知' },
  { text: '求知是人类的本性。', author: '亚里士多德', tag: '求知' },
  { text: '真理是时间的女儿。', author: '培根', tag: '求知' },
  { text: '真正的发现之旅，不在于寻找新天地，而在于拥有新眼光。', author: '普鲁斯特', tag: '求知' },
  { text: '独学而无友，则孤陋而寡闻。', author: '《礼记·学记》', tag: '求知' },
  // —— 科学 ——
  { text: '如果我看得更远，那是因为我站在巨人的肩膀上。', author: '牛顿', tag: '科学' },
  { text: '想象力比知识更重要。', author: '爱因斯坦', tag: '科学' },
  { text: '一切都应尽可能简单，但不应过于简单。', author: '爱因斯坦', tag: '科学' },
  { text: '自然界不做无谓的跳跃。', author: '莱布尼茨', tag: '科学' },
  { text: '数学是科学的女王。', author: '高斯', tag: '科学' },
  // —— 耐心 ——
  { text: '欲速则不达。', author: '孔子', tag: '耐心' },
  { text: '千里之行，始于足下。', author: '老子', tag: '耐心' },
  { text: '锲而不舍，金石可镂。', author: '荀子', tag: '耐心' },
  { text: '跬步不休，跛鳖千里。', author: '荀子', tag: '耐心' },
  { text: '忍耐是苦的，但它的果实是甜的。', author: '卢梭', tag: '耐心' },
  { text: '万事皆有定时。', author: '《传道书》', tag: '耐心' },
  // —— 相遇 ——
  { text: '有朋自远方来，不亦乐乎。', author: '孔子', tag: '相遇' },
  { text: '一个人走得快，一群人走得远。', author: '非洲谚语', tag: '相遇' },
  { text: '嘤其鸣矣，求其友声。', author: '《诗经》', tag: '相遇' },
  { text: '相知无远近，万里尚为邻。', author: '张九龄', tag: '相遇' },
  { text: '海内存知己，天涯若比邻。', author: '王勃', tag: '相遇' },
  // —— 自省 ——
  { text: '未经审视的人生，是不值得过的。', author: '苏格拉底', tag: '自省' },
  { text: '认识你自己。', author: '德尔斐神庙箴言', tag: '自省' },
  { text: '知人者智，自知者明。', author: '老子', tag: '自省' },
  { text: '吾日三省吾身。', author: '曾子', tag: '自省' },
  { text: '人是一根会思想的苇草。', author: '帕斯卡', tag: '自省' },
  { text: '我思，故我在。', author: '笛卡尔', tag: '自省' },
  { text: '人是自己选择的总和。', author: '萨特', tag: '自省' },
  { text: '当你凝视深渊时，深渊也在凝视你。', author: '尼采', tag: '自省' },
  { text: '在隆冬，我终于知道，我身上有一个不可战胜的夏天。', author: '加缪', tag: '自省' },
  { text: '参差多态，乃是幸福的本源。', author: '罗素', tag: '自省' },
  // —— 诗意 ——
  { text: '人，诗意地栖居。', author: '荷尔德林', tag: '诗意' },
  { text: '我们都在阴沟里，但仍有人仰望星空。', author: '王尔德', tag: '诗意' },
  { text: '采菊东篱下，悠然见南山。', author: '陶渊明', tag: '诗意' },
  { text: '长风破浪会有时，直挂云帆济沧海。', author: '李白', tag: '诗意' },
  { text: '不畏浮云遮望眼，自缘身在最高层。', author: '王安石', tag: '诗意' },
  // —— 告别 ——
  { text: '逝者如斯夫，不舍昼夜。', author: '孔子', tag: '告别' },
  { text: '人生天地间，忽如远行客。', author: '《古诗十九首》', tag: '告别' },
  { text: '相见时难别亦难。', author: '李商隐', tag: '告别' },
  { text: '一切有为法，如梦幻泡影。', author: '《金刚经》', tag: '告别' },
] as const

/** 场景 → 标签组（每个文案槽位用哪个场景，见 `components/QuoteLine.tsx` 的调用点）。 */
export const QUOTE_SCENES = {
  /** 首页主视觉：求知与自省的混合气质 */
  hero: ['求知', '自省', '诗意'],
  /** 学习/创建房间/登录注册：求知 */
  learn: ['求知', '科学'],
  /** 等待室：耐心 */
  patience: ['耐心'],
  /** 空房间、空消息、空成员：相遇 */
  meet: ['相遇', '求知'],
  /** 个人信息、未登录、需要登录：自省 */
  self: ['自省'],
  /** 房间结束、失效链接：告别 */
  farewell: ['告别', '诗意'],
  /** 纯诗意场合 */
  poetics: ['诗意'],
} as const satisfies Record<string, readonly QuoteTag[]>

export type QuoteScene = keyof typeof QUOTE_SCENES

/** 从某个场景的标签组里随机取一句；`random` 可注入（用例里传固定值以便断言）。 */
export function pickQuote(scene: QuoteScene, random: () => number = Math.random): PhilosophyQuote {
  const tags = QUOTE_SCENES[scene] as readonly QuoteTag[]
  const pool = PHILOSOPHY_QUOTES.filter((item) => tags.includes(item.tag))
  const source = pool.length > 0 ? pool : PHILOSOPHY_QUOTES
  const index = Math.min(source.length - 1, Math.max(0, Math.floor(random() * source.length)))
  return source[index]
}
