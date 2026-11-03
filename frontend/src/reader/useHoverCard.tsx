import { useCallback, useRef, useState } from 'react'
import { getDefinition, getPopup, type Item, type Popup } from '../api'

const HOVER_DELAY_MS = 350

// The first meaning of a word as one line ("noun: a house"), or '' when there is none or no connection.
async function firstMeaning(languageId: number, text: string): Promise<string> {
  try {
    const found = await getDefinition(languageId, text)
    // For an inflected form the base form's meaning is the useful one ("szkoła: school").
    const base = found.lemmas?.[0]
    if (base?.entries[0]) return `${base.word}: ${base.entries[0].definitions[0].text}`
    const entry = found.found ? found.entries?.[0] : undefined
    return entry ? `${entry.partOfSpeech.toLowerCase()}: ${entry.definitions[0].text}` : ''
  } catch {
    return ''
  }
}

// A small card with a word's translation, shown when the pointer rests on it.
// Popups are cached per term; call forget() after a term changes.
export function useHoverCard() {
  const [hover, setHover] = useState<{ popup: Popup; meaning: string; x: number; y: number } | null>(null)
  const cache = useRef(new Map<number, Popup>())
  const meanings = useRef(new Map<string, string>()) // first Wiktionary meaning per word, kept for the session
  const timer = useRef<number | undefined>(undefined)
  const ticket = useRef(0) // each hover gets a number; a slow answer for an earlier hover is dropped

  const start = useCallback((it: Item, el: HTMLElement, languageId?: number) => {
    window.clearTimeout(timer.current)
    if (it.termId === null) return
    const id = it.termId
    const mine = ++ticket.current
    timer.current = window.setTimeout(async () => {
      let popup = cache.current.get(id)
      if (!popup) {
        popup = await getPopup(id).catch(() => undefined)
        if (popup) cache.current.set(id, popup)
      }
      if (!popup || mine !== ticket.current) return
      // A word with no translation of yours yet shows its first meaning from Wiktionary.
      let meaning = ''
      if (!popup.translation && languageId !== undefined) {
        const key = `${languageId}:${popup.text}`
        meaning = meanings.current.get(key) ?? (await firstMeaning(languageId, popup.text))
        meanings.current.set(key, meaning)
        if (mine !== ticket.current) return
      }
      if (!(popup.translation || meaning || popup.image || popup.tags.length || popup.parents.length)) return
      const r = el.getBoundingClientRect()
      setHover({ popup, meaning, x: Math.min(r.left, window.innerWidth - 280), y: r.bottom + 6 })
    }, HOVER_DELAY_MS)
  }, [])

  const end = useCallback(() => {
    window.clearTimeout(timer.current)
    ticket.current++
    setHover(null)
  }, [])

  const forget = useCallback((termId: number) => cache.current.delete(termId), [])
  const forgetAll = useCallback(() => cache.current.clear(), [])

  const card = hover && (
    <div className="hover-card" style={{ left: hover.x, top: hover.y }}>
      <b>{hover.popup.text}</b>
      {hover.popup.romanization && <span className="muted"> {hover.popup.romanization}</span>}
      {hover.popup.translation && <div>{hover.popup.translation}</div>}
      {hover.meaning && <div className="muted">{hover.meaning}</div>}
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
