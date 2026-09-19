/** 主题 → 图标（r007；单一图标库 lucide-react）。
 *
 * 图标放 UI 层，不放进 `api/rooms.ts`（那是接口契约层，不引入 React 组件）。
 */
import {
  BookOpen,
  Castle,
  Cpu,
  Dna,
  Feather,
  Globe,
  Hash,
  Landmark,
  PenLine,
  Percent,
  Scale,
  Scroll,
  Sigma,
  Table,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

import type { Topic } from '../api/rooms'

export const TOPIC_ICONS: Record<Topic, LucideIcon> = {
  epicureanism: Scroll,
  'math-biology': Dna,
  'german-history': Landmark,
  'philosophy-history': BookOpen,
  'chinese-philosophy': Feather,
  ethics: Scale,
  'modern-history': Globe,
  'ancient-china': Castle,
  'mathematical-analysis': Sigma,
  'linear-algebra': Table,
  'probability-statistics': Percent,
  'number-theory': Hash,
  'machine-learning': Cpu,
  custom: PenLine,
}
