import { useState } from 'react'
import { getPref, setPref } from './api'
import { HOVER_DELAYS, HOVER_PREFS } from './reader/useHoverCard'
import { SettingRow, SettingsGroup, Toggle } from './SettingsKit'

// What happens when the pointer rests on a word in the reader.
export function HoverSettings() {
  const [hoverOn, setHoverOn] = useState(() => getPref<boolean>(HOVER_PREFS.enabled, true))
  const [hoverDelay, setHoverDelay] = useState(() => getPref<number>(HOVER_PREFS.delay, 350))
  return (
    <SettingsGroup title="Reading">
      <SettingRow label="Meaning on hover" info="Shows a word's meaning when the pointer rests on it: your own translation first; if there is none, the first meaning from your dictionaries.">
        <Toggle
          label="Meaning on hover"
          checked={hoverOn}
          onChange={(on) => {
            setHoverOn(on)
            setPref(HOVER_PREFS.enabled, on)
          }}
        />
      </SettingRow>
      <SettingRow label="Wait before showing" disabled={!hoverOn}>
        <select
          aria-label="Wait before showing"
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
      </SettingRow>
    </SettingsGroup>
  )
}
