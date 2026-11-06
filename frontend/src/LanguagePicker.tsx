import { useMemo, useState } from 'react'
import type { LanguageSupport } from './api'
import { matching, splitLanguages, toggled } from './languageChoice'
import { levelLabel } from './languageSupport'

// First run: the languages you chose as pills with an "Add languages" button next to them; the picker shows the most studied languages and a search for the rest.
export function LanguagePicker({ available, chosen, support, onChange }: { available: string[]; chosen: string[]; support: Record<string, LanguageSupport>; onChange: (chosen: string[]) => void }) {
  const [open, setOpen] = useState(true)
  const [more, setMore] = useState(false)
  const [query, setQuery] = useState('')
  const { popular } = useMemo(() => splitLanguages(available), [available])
  const everyone = useMemo(() => [...available].sort((a, b) => a.localeCompare(b)), [available])
  const found = matching(everyone, query)
  const full = (name: string) => support[name]?.level === 'full'
  const choose = (name: string) => onChange(toggled(chosen, name))

  const chip = (name: string) => (
    <button
      key={name}
      type="button"
      className={`lang-chip${chosen.includes(name) ? ' on' : ''}`}
      aria-pressed={chosen.includes(name)}
      aria-label={support[name] ? `${name}, ${levelLabel(support[name].level).toLowerCase()}` : name}
      title={support[name] ? levelLabel(support[name].level) : undefined}
      onClick={() => choose(name)}
    >
      {name}
      {full(name) && <span className="lang-full">✓</span>}
    </button>
  )

  return (
    <div className="lang-picker">
      <div className="lang-chosen" aria-label="Your languages">
        {chosen.length === 0 && <span className="muted">No language yet</span>}
        {chosen.map((name) => (
          <span key={name} className="lang-pill">
            {name}
            <button type="button" className="lang-x" aria-label={`Remove ${name}`} onClick={() => choose(name)}>
              ×
            </button>
          </span>
        ))}
        {(chosen.length > 0 || !open) && (
          <button type="button" className="secondary" aria-expanded={open} onClick={() => setOpen(!open)}>
            {open ? 'Done adding' : 'Add languages'}
          </button>
        )}
      </div>

      {open && (
        <div className="lang-panel">
          <div className="lang-chips">{popular.map(chip)}</div>
          <p className="muted lang-legend">✓ Full support: meanings, an AI voice and translation, all local. Other languages work for reading, with online meanings and the Mac voice.</p>
          {!more ? (
            <button type="button" className="link-button" onClick={() => setMore(true)}>
              More languages…
            </button>
          ) : (
            <>
              <input
                autoFocus
                value={query}
                placeholder="Search languages"
                aria-label="Search languages"
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && found.length > 0) {
                    e.preventDefault()
                    onChange(chosen.includes(found[0]) ? chosen : [...chosen, found[0]])
                    setQuery('')
                  }
                  if (e.key === 'Backspace' && query === '' && chosen.length > 0) onChange(chosen.slice(0, -1))
                }}
              />
              <div className="lang-chips">
                {query.trim() === '' ? (
                  <span className="muted">Type a language name ({available.length} languages).</span>
                ) : found.length > 0 ? (
                  found.map(chip)
                ) : (
                  <span className="muted">No language matches.</span>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
