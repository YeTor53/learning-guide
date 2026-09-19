import { useEffect, useState } from 'react'

/** 窄屏判定：与 `global.css` 的 `@media (max-width: 900px)` 保持同一阈值。
 *
 * r004 cp-3 用途：窄屏下侧边栏会变成**顶部横向条**，此时「收起侧边栏」既无意义、
 * 又会让横向条只剩图标（React 里 `collapsed` 会直接不渲染 label，CSS 救不回来）。
 * 因此窄屏时强制按「展开」渲染并隐藏折叠按钮。
 */
export const NARROW_QUERY = '(max-width: 900px)'

export default function useNarrowStrip(): boolean {
  const [narrow, setNarrow] = useState<boolean>(
    () => typeof window !== 'undefined' && window.matchMedia(NARROW_QUERY).matches,
  )

  useEffect(() => {
    const mq = window.matchMedia(NARROW_QUERY)
    const onChange = () => setNarrow(mq.matches)
    onChange()
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])

  return narrow
}
