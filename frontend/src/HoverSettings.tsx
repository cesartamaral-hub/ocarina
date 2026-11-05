import { useState } from 'react'
import { getPref, setPref } from './api'
import { HOVER_DELAYS, HOVER_PREFS } from './reader/useHoverCard'

// What happens when the pointer rests on a word in the reader.
export function HoverSettings() {
  const [hoverOn, setHoverOn] = useState(() => getPref<boolean>(HOVER_PREFS.enabled, true))
  const [hoverDelay, setHoverDelay] = useState(() => getPref<number>(HOVER_PREFS.delay, 350))
  return (
        <section className="ap-card">
          <h2>Hovering over words</h2>
          <label className="ap-check">
            <input
              type="checkbox"
              checked={hoverOn}
              onChange={(e) => {
                setHoverOn(e.target.checked)
                setPref(HOVER_PREFS.enabled, e.target.checked)
              }}
            />
            Show a word's meaning when the pointer rests on it
          </label>
          <label className="ap-field">
            <span>Wait first</span>
            <select
              value={hoverDelay}
              disabled={!hoverOn}
              onChange={(e) => {
                setHoverDelay(Number(e.target.value))
                setPref(HOVER_PREFS.delay, Number(e.target.value))
              }}
            >
              {HOVER_DELAYS.map((d) => (
                <option key={d.ms} value={d.ms}>
                  {d.label}
                </option>
              ))}
            </select>
          </label>
          <p className="muted ap-note">Your own translation first; if there is none, the first meaning from your dictionaries.</p>
        </section>
  )
}
