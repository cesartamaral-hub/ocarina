import { useState } from 'react'
import { PRONOUNCE_SOURCES, getPref, setPref, type PronounceSource } from './api'
import { SettingRow, SettingsGroup } from './SettingsKit'

// Which source says a word when you press the speaker button or S in the reader (the arrow next to the button picks another one for one time).
export function Pronunciation() {
  const [source, setSource] = useState(() => getPref<PronounceSource>('pronounce.source', 'auto'))
  return (
    <SettingsGroup title="Hearing words">
      <p className="set-note muted">
        Select a word in the reader and press the speaker button, or S. When the source you choose cannot say it (no model, no recording, no internet), the Mac system voice does.
      </p>
      {PRONOUNCE_SOURCES.map((s) => (
        <SettingRow key={s.id} label={s.name} info={s.detail}>
          <input
            type="radio"
            className="set-radio"
            name="pronounce-source"
            aria-label={s.name}
            checked={source === s.id}
            onChange={() => {
              setSource(s.id)
              setPref('pronounce.source', s.id)
            }}
          />
        </SettingRow>
      ))}
    </SettingsGroup>
  )
}
