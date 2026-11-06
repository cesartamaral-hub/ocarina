import { useEffect, useState } from 'react'
import { ACTIONS, assignKey, keyLabel, keyOf, resetKeys } from './shortcutKeys'
import { useEscape } from './escape'
import { setPref } from './api'
import { SettingRow, SettingsGroup } from './SettingsKit'
import { KEY_TARGETS, KEY_TARGET_PREF, keyTarget } from './reader/keyTarget'

export function Shortcuts() {
  const [listening, setListening] = useState<string | null>(null)
  const [, setVersion] = useState(0)
  const [error, setError] = useState('')
  const [target, setTarget] = useState(keyTarget)

  useEscape(listening !== null, () => setListening(null))

  // While an action is waiting for its new key, the next key press is that key.
  useEffect(() => {
    if (!listening) return
    function onKey(e: KeyboardEvent) {
      e.preventDefault()
      e.stopPropagation()
      const problem = assignKey(listening!, e.key)
      setError(problem ?? '')
      if (!problem) {
        setListening(null)
        setVersion((v) => v + 1)
      }
    }
    window.addEventListener('keydown', onKey, true)
    return () => window.removeEventListener('keydown', onKey, true)
  }, [listening])

  return (
    <>
      <h1>Keyboard shortcuts</h1>
      {error && <p className="error">{error}</p>}
      <SettingsGroup title="Status and speak keys">
        <SettingRow label="Act on" info="Which word the status keys and the speak key use when there is both a word under the pointer and a selected word.">
          <select
            aria-label="The status keys and the speak key act on"
            value={target}
            onChange={(e) => {
              setTarget(e.target.value as typeof target)
              setPref(KEY_TARGET_PREF, e.target.value)
            }}
          >
            {KEY_TARGETS.map((t) => (
              <option key={t.id} value={t.id}>
                {t.label}
              </option>
            ))}
          </select>
        </SettingRow>
      </SettingsGroup>
      <SettingsGroup title="Keys in the reader">
        <p className="set-note muted">Click a key, then press the one you want instead. Esc cancels.</p>
        {ACTIONS.map((a) => (
          <SettingRow key={a.id} label={a.label}>
            <button className="secondary key" onClick={() => (setError(''), setListening(listening === a.id ? null : a.id))}>
              {listening === a.id ? 'Press a key…' : <kbd>{keyLabel(keyOf(a.id))}</kbd>}
            </button>
          </SettingRow>
        ))}
        <SettingRow label="Standard keys">
          <button
            className="secondary"
            onClick={() => {
              resetKeys()
              setListening(null)
              setError('')
              setVersion((v) => v + 1)
            }}
          >
            Back to the standard keys
          </button>
        </SettingRow>
      </SettingsGroup>
    </>
  )
}
