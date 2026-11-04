import { useCallback, useEffect, useRef, useState } from 'react'
import { getDefinition, getPopup, getPref, type Item, type Popup } from '../api'
import { useEscape } from '../escape'

// Settings (Appearance page): whether the card shows, and how long the pointer rests on a word first.
export const HOVER_PREFS = { enabled: 'reader.hoverMeaning', delay: 'reader.hoverDelay' }
export const HOVER_DELAYS = [
  { ms: 150, label: 'Quick' },
  { ms: 350, label: 'Normal' },
  { ms: 700, label: 'Slow' },
]

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
  const [hover, setHover] = useState<{ popup: Popup; meaning: string; x: number; y: number; above: boolean } | null>(null)
  const cache = useRef(new Map<number, Popup>())
  const meanings = useRef(new Map<string, string>()) // first Wiktionary meaning per word, kept for the session
  const timer = useRef<number | undefined>(undefined)
  const ticket = useRef(0) // each hover gets a number; a slow answer for an earlier hover is dropped

  const start = useCallback((it: Item, el: HTMLElement, languageId?: number) => {
    window.clearTimeout(timer.current)
    if (!getPref(HOVER_PREFS.enabled, true)) return
    const id = it.termId
    const mine = ++ticket.current
    timer.current = window.setTimeout(async () => {
      // A word you have never opened has no term yet: its card has only what the dictionary says.
      let popup: Popup | undefined = id === null ? undefined : cache.current.get(id)
      if (id !== null && !popup) {
        popup = await getPopup(id).catch(() => undefined)
        if (popup) cache.current.set(id, popup)
      }
      if (id === null) popup = { id: 0, text: it.text, status: 0, translation: '', romanization: '', tags: [], parents: [], image: null }
      if (!popup || mine !== ticket.current) return
      // A word with no translation of yours yet shows its first meaning from Wiktionary.
      let meaning = ''
      if (!popup.translation && languageId !== undefined) {
        const key = `${languageId}:${popup.text.toLowerCase()}`
        meaning = meanings.current.get(key) ?? (await firstMeaning(languageId, popup.text))
        meanings.current.set(key, meaning)
        if (mine !== ticket.current) return
      }
      const r = el.getBoundingClientRect()
      const above = r.bottom + 170 > window.innerHeight && r.top > 170 // no room below, room above
      setHover({ popup, meaning, x: Math.max(8, Math.min(r.left, window.innerWidth - 292)), y: above ? window.innerHeight - r.top + 6 : r.bottom + 6, above })
    }, getPref<number>(HOVER_PREFS.delay, 350))
  }, [])

  const end = useCallback(() => {
    window.clearTimeout(timer.current)
    ticket.current++
    setHover(null)
  }, [])

  // The card goes away when the page moves under it, on any click or key, and on Esc.
  const showing = hover !== null
  useEscape(showing, end)
  useEffect(() => {
    if (!showing) return
    const hide = () => end()
    window.addEventListener('scroll', hide, true)
    window.addEventListener('mousedown', hide, true)
    return () => {
      window.removeEventListener('scroll', hide, true)
      window.removeEventListener('mousedown', hide, true)
    }
  }, [showing, end])

  const forget = useCallback((termId: number) => cache.current.delete(termId), [])
  const forgetAll = useCallback(() => cache.current.clear(), [])

  const card = hover && (
    <div className="hover-card" role="tooltip" style={hover.above ? { left: hover.x, bottom: hover.y } : { left: hover.x, top: hover.y }}>
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
      {!hover.popup.translation && !hover.meaning && hover.popup.parents.length === 0 && <div className="muted">No meaning yet. Click the word to look it up.</div>}
      {hover.popup.image && <img src={hover.popup.image} alt="" />}
    </div>
  )

  return { start, end, forget, forgetAll, card }
}
