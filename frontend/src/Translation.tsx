import { useEffect, useState } from 'react'
import { getTranslateSettings, putTranslateSettings, type TranslateSettings } from './api'
import { useOffline } from './offline'
import { formatBytes } from './format'
import { notify } from './notices'
import { SPEECH_LANGUAGES } from './speechLanguages'
import { SettingRow, SettingsGroup } from './SettingsKit'
import { NoLocalModelNotice } from './NoLocalModelNotice'
import { TryTranslation } from './TryTranslation'

export function Translation() {
  const offline = useOffline()
  const [s, setS] = useState<TranslateSettings | null>(null)
  const [email, setEmail] = useState('')
  const [key, setKey] = useState('')
  const [error, setError] = useState('')
  useEffect(() => {
    getTranslateSettings().then(
      (loaded) => {
        setS(loaded)
        setEmail(loaded.email)
      },
      (e) => setError(e.message),
    )
  }, [])

  async function save(change: Parameters<typeof putTranslateSettings>[0], message?: string) {
    setError('')
    try {
      const next = await putTranslateSettings(change)
      setS(next)
      if (message) notify(message)
    } catch (e) {
      setError((e as Error).message)
    }
  }

  if (!s) return error ? <p className="error">{error}</p> : <p className="muted">Loading…</p>
  const short = (name: string) => name.replace(/\s*\(.*\)\s*$/, '')
  return (
    <>
      <h1>Sentence translation</h1>
      {error && <p className="error">{error}</p>}

      <SettingsGroup title="Service">
        {offline && !s.localModels.some((m) => m.installed) && (
          <p className="set-note">
            <NoLocalModelNotice />
          </p>
        )}
        <p className="set-note muted">
          When you press “Translate sentence” in the reader, that sentence is sent to the service you choose here. Nothing is sent unless you press it, and translations you have seen are saved locally.
        </p>
        {s.providers.map((p) => {
          const needsNet = offline && p.id !== 'local'
          const missing = (p.id === 'local' && !s.localModel.installed) || needsNet
          return (
            <SettingRow key={p.id} label={p.name} info={p.description} disabled={missing}>
              {needsNet && <span className="muted">Needs the internet</span>}
              {missing && !needsNet && (
                <span className="muted">
                  Not downloaded ({formatBytes(s.localModel.sizeBytes)}) · <a href="#/settings/models">Download</a>
                </span>
              )}
              <input type="radio" className="set-radio" name="provider" aria-label={p.name} disabled={missing} checked={s.provider === p.id} onChange={() => save({ provider: p.id })} />
            </SettingRow>
          )
        })}
      </SettingsGroup>

      <SettingsGroup title="Translation">
        <SettingRow label="Translate into">
          <select aria-label="Translate into" value={s.target} onChange={(e) => save({ target: e.target.value })}>
            {s.targets.map((t) => (
              <option key={t.code} value={t.code}>
                {t.name}
              </option>
            ))}
          </select>
        </SettingRow>

        {s.provider === 'local' && (
          <SettingRow label="Local model" info="The translation model that runs locally. Chosen per language under Models.">
            <span className="muted">
              {s.localAuto && s.localModels.filter((m) => m.installed).length > 1 ? 'Automatic: the best of your models for each language' : short(s.localModel.name)}
              {Object.entries(s.localModelByLanguage ?? {}).map(([code, id]) => (
                <span key={code}>
                  {' '}
                  · {SPEECH_LANGUAGES[code] ?? code.toUpperCase()}: {short(s.localModels.find((m) => m.id === id)?.name ?? id)}
                </span>
              ))}
            </span>
            <a href="#/settings/models">Change</a>
          </SettingRow>
        )}

        {s.provider === 'mymemory' && (
          <SettingRow label="Email address" info="Optional. MyMemory allows ten times more translations a day when it knows an address. It is used for that and nothing else.">
            <input className="set-input" type="email" aria-label="Email address" value={email} placeholder="you@example.com" onChange={(e) => setEmail(e.target.value)} />
            <button className="secondary" disabled={email === s.email} onClick={() => save({ email }, 'Saved')}>
              Save
            </button>
          </SettingRow>
        )}

        {s.provider === 'deepl' && (
          <SettingRow label="DeepL API key" info="Get a free key at deepl.com (“DeepL API Free”). It is kept in a private file in the Ocarina data folder, and never shown again.">
            {s.hasDeeplKey ? (
              <>
                <span className="muted">Saved ({s.deeplKeyHint})</span>
                <button className="secondary" onClick={() => save({ deeplKey: '' }, 'Key removed')}>
                  Remove
                </button>
              </>
            ) : (
              <>
                <input className="set-input" type="password" aria-label="DeepL API key" autoComplete="off" value={key} placeholder="Paste your key" onChange={(e) => setKey(e.target.value)} />
                <button
                  disabled={!key.trim()}
                  onClick={() => {
                    save({ deeplKey: key }, 'Key saved')
                    setKey('')
                  }}
                >
                  Save key
                </button>
              </>
            )}
          </SettingRow>
        )}

      </SettingsGroup>

      <TryTranslation s={s} />
    </>
  )
}
