import { useState } from 'react'
import { PRONOUNCE_SOURCES, getPref, setPref, type PronounceSource } from './api'

// Which source says a word when you press the speaker button or S in the reader (the arrow next to the button picks another one for one time).
export function Pronunciation() {
  const [source, setSource] = useState(() => getPref<PronounceSource>('pronounce.source', 'voice'))
  return (
    <>
      <h2>Hearing words</h2>
      <p className="muted">
        Select a word or some words in the reader and press the speaker button, or the S key. When the source you choose cannot say it (no model, no recording, no internet), the voice of this Mac does.
      </p>
      <fieldset className="pronounce-sources">
        <legend className="muted">Say words with</legend>
        {PRONOUNCE_SOURCES.map((s) => (
          <label key={s.id}>
            <input
              type="radio"
              name="pronounce-source"
              checked={source === s.id}
              onChange={() => {
                setSource(s.id)
                setPref('pronounce.source', s.id)
              }}
            />
            <span>
              {s.name}
              <small className="muted">{s.detail}</small>
            </span>
          </label>
        ))}
      </fieldset>
    </>
  )
}
