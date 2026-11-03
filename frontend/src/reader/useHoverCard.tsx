import { useCallback, useRef, useState } from 'react'
import { getPopup, type Item, type Popup } from '../api'

const HOVER_DELAY_MS = 350

// A small card with a word's translation, shown when the pointer rests on it.
// Popups are cached per term; call forget() after a term changes.
export function useHoverCard() {
  const [hover, setHover] = useState<{ popup: Popup; x: number; y: number } | null>(null)
  const cache = useRef(new Map<number, Popup>())
  const timer = useRef<number | undefined>(undefined)

  const start = useCallback((it: Item, el: HTMLElement) => {
    window.clearTimeout(timer.current)
    if (it.termId === null) return
    const id = it.termId
    timer.current = window.setTimeout(async () => {
      let popup = cache.current.get(id)
      if (!popup) {
        popup = await getPopup(id).catch(() => undefined)
        if (popup) cache.current.set(id, popup)
      }
      if (!popup || !(popup.translation || popup.image || popup.tags.length || popup.parents.length)) return
      const r = el.getBoundingClientRect()
      setHover({ popup, x: Math.min(r.left, window.innerWidth - 280), y: r.bottom + 6 })
    }, HOVER_DELAY_MS)
  }, [])

  const end = useCallback(() => {
    window.clearTimeout(timer.current)
    setHover(null)
  }, [])

  const forget = useCallback((termId: number) => cache.current.delete(termId), [])
  const forgetAll = useCallback(() => cache.current.clear(), [])

  const card = hover && (
    <div className="hover-card" style={{ left: hover.x, top: hover.y }}>
      <b>{hover.popup.text}</b>
      {hover.popup.romanization && <span className="muted"> {hover.popup.romanization}</span>}
      {hover.popup.translation && <div>{hover.popup.translation}</div>}
      {hover.popup.parents.map((p, i) => (
        <div key={i} className="muted">
          {p.text}: {p.translation}
        </div>
      ))}
      {hover.popup.tags.length > 0 && <div className="muted">{hover.popup.tags.join(', ')}</div>}
      {hover.popup.image && <img src={hover.popup.image} alt="" />}
    </div>
  )

  return { start, end, forget, forgetAll, card }
}
