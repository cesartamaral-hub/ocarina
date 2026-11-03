import { useSyncExternalStore } from 'react'
import { currentNotices, subscribeNotices } from './notices'

export function NoticeList() {
  const list = useSyncExternalStore(subscribeNotices, currentNotices)
  if (list.length === 0) return null
  return (
    <div className="notices" role="status" aria-live="polite">
      {list.map((n) => (
        <div key={n.id}>{n.text}</div>
      ))}
    </div>
  )
}
