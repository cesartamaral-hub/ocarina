import { useEffect, useMemo, useRef, useState } from 'react'
import type { LanguageSupport } from './api'
import { alphabetical, matching, moved } from './languageChoice'
import { levelLabel } from './languageSupport'

// First run: a short scrolling list of languages (A to Z, with a search) on the left; the ones you pick move to "Your languages" on the right.
export function LanguagePicker({ available, chosen, support, onChange }: { available: string[]; chosen: string[]; support: Record<string, LanguageSupport>; onChange: (chosen: string[]) => void }) {
  const [query, setQuery] = useState('')
  const [active, setActive] = useState(0)
  const list = useRef<HTMLUListElement>(null)
  const everyone = useMemo(() => alphabetical(available), [available])
  const shown = matching(
    everyone.filter((n) => !chosen.includes(n)),
    query,
  )
  const at = Math.min(active, Math.max(shown.length - 1, 0))

  useEffect(() => {
    list.current?.querySelector('[aria-selected="true"]')?.scrollIntoView({ block: 'nearest' })
  }, [at, shown.length])

  const add = (name: string) => {
    onChange([...chosen, name])
    setQuery('')
  }
  const full = (name: string) => support[name]?.level === 'full'

  return (
    <div className="lang-picker">
      <div className="lang-pane">
        <input
          value={query}
          placeholder="Search languages"
          aria-label="Search languages"
          role="combobox"
          aria-expanded="true"
          aria-controls="lang-list"
          onChange={(e) => {
            setQuery(e.target.value)
            setActive(0)
          }}
          onKeyDown={(e) => {
            if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
              e.preventDefault()
              setActive(moved(at, e.key, shown.length))
            } else if (e.key === 'Enter' && shown.length > 0) {
              e.preventDefault()
              add(shown[at])
            } else if (e.key === 'Backspace' && query === '' && chosen.length > 0) onChange(chosen.slice(0, -1))
          }}
        />
        <ul id="lang-list" ref={list} className="lang-list" role="listbox" aria-label="Languages">
          {shown.length === 0 && <li className="muted lang-empty">{available.length === chosen.length ? 'You have picked them all.' : 'No language matches.'}</li>}
          {shown.map((name, i) => (
            <li key={name} role="option" aria-selected={i === at} className={i === at ? 'on' : ''} onMouseEnter={() => setActive(i)} onClick={() => add(name)}>
              <span>{name}</span>
              {full(name) && (
                <span className="lang-full" title={levelLabel('full')}>
                  ✓
                </span>
              )}
            </li>
          ))}
        </ul>
      </div>
      <div className="lang-pane lang-picked" aria-label="Your languages">
        <h2>Your languages{chosen.length > 0 ? ` (${chosen.length})` : ''}</h2>
        {chosen.length === 0 ? (
          <p className="muted">Pick the languages you study from the list.</p>
        ) : (
          <ul>
            {chosen.map((name) => (
              <li key={name}>
                <span>
                  {name}
                  {full(name) && <span className="lang-full"> ✓</span>}
                </span>
                <button type="button" className="lang-x" aria-label={`Remove ${name}`} onClick={() => onChange(chosen.filter((n) => n !== name))}>
                  ×
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
      <p className="muted lang-legend">✓ Full support: meanings, an AI voice and translation, all local. Other languages work for reading, with online meanings and the Mac voice.</p>
    </div>
  )
}
