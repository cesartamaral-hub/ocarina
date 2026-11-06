import { useState } from 'react'
import { getPref, setPref, type Language } from './api'
import { SettingRow, SettingsGroup, Toggle } from './SettingsKit'

const GOALS = [100, 250, 500, 1000, 2000, 5000, 10000]

// Per language: the goal of the progress bar on the Books page (or the next step, automatically), and whether the words you already know count as learned.
export function ProgressSettings({ languages }: { languages: Language[] }) {
  const [, setVersion] = useState(0)
  if (languages.length === 0) return null
  return (
    <SettingsGroup title="Progress in the app">
      <p className="set-note muted">The bar on the Books page counts the words you learned in Ocarina: taken to Known by you, not marked known when finishing a page.</p>
      {languages.map((l) => {
        const goal = getPref<number | null>(`learned.goal.${l.id}`, null)
        const prior = getPref<boolean>(`learned.prior.${l.id}`, false)
        return (
          <SettingRow key={l.id} label={l.name} info="Goal: the number the bar works towards. Count what I already know: the words that are Known now, from before, are counted as learned too.">
            <select
              aria-label={`Goal for ${l.name}`}
              value={goal ?? ''}
              onChange={(e) => {
                setPref(`learned.goal.${l.id}`, e.target.value ? Number(e.target.value) : null)
                setVersion((v) => v + 1)
              }}
            >
              <option value="">Next step</option>
              {GOALS.map((g) => (
                <option key={g} value={g}>
                  {g.toLocaleString()} words
                </option>
              ))}
            </select>
            <span className="muted">Count what I already know</span>
            <Toggle
              label={`Count what I already know in ${l.name}`}
              checked={prior}
              onChange={(on) => {
                setPref(`learned.prior.${l.id}`, on)
                setVersion((v) => v + 1)
              }}
            />
          </SettingRow>
        )
      })}
    </SettingsGroup>
  )
}
