import { useEffect, useState } from 'react'
import { compareModels, getLanguages, getTranslateSettings, putTranslateSettings, testTranslation, type Comparison, type Language, type TranslateSettings, type Translation as Result } from './api'
import { useOffline } from './offline'
import { formatBytes } from './format'
import { notify } from './notices'
import { SPEECH_LANGUAGES } from './speechLanguages'
import { SettingRow, SettingsGroup } from './SettingsKit'

export function Translation() {
  const offline = useOffline()
  const [s, setS] = useState<TranslateSettings | null>(null)
  const [email, setEmail] = useState('')
  const [key, setKey] = useState('')
  const [error, setError] = useState('')
  const [test, setTest] = useState<{ busy: boolean; ok?: Result; error?: string }>({ busy: false })
  const [languages, setLanguages] = useState<Language[]>([])
  const [compare, setCompare] = useState<{ languageId: number | null; text: string; busy: boolean; results?: Comparison[]; error?: string }>({
    languageId: null,
    text: 'Goedemorgen, hoe gaat het met je? Ik hoop dat je een fijne dag hebt.',
    busy: false,
  })

  useEffect(() => {
    getTranslateSettings().then(
      (loaded) => {
        setS(loaded)
        setEmail(loaded.email)
      },
      (e) => setError(e.message),
    )
  }, [])

  useEffect(() => {
    getLanguages().then(setLanguages, () => undefined)
  }, [])

  async function runCompare() {
    const languageId = compare.languageId ?? languages[0]?.id
    if (languageId === undefined) return
    setCompare((c) => ({ ...c, busy: true, results: undefined, error: undefined }))
    try {
      const { results } = await compareModels(languageId, compare.text)
      setCompare((c) => ({ ...c, busy: false, results }))
    } catch (e) {
      setCompare((c) => ({ ...c, busy: false, error: (e as Error).message }))
    }
  }

  async function save(change: Parameters<typeof putTranslateSettings>[0], message?: string) {
    setError('')
    try {
      const next = await putTranslateSettings(change)
      setS(next)
      setTest({ busy: false })
      if (message) notify(message)
    } catch (e) {
      setError((e as Error).message)
    }
  }

  async function runTest() {
    setTest({ busy: true })
    try {
      setTest({ busy: false, ok: await testTranslation() })
    } catch (e) {
      setTest({ busy: false, error: (e as Error).message })
    }
  }

  if (!s) return error ? <p className="error">{error}</p> : <p className="muted">Loading…</p>
  const short = (name: string) => name.replace(/\s*\(.*\)\s*$/, '')
  return (
    <>
      <h1>Sentence translation</h1>
      {error && <p className="error">{error}</p>}

      <SettingsGroup title="Service">
        <p className="set-note muted">
          When you press “Translate sentence” in the reader, that sentence is sent to the service you choose here. Nothing is sent unless you press it, and translations you have seen are saved on this Mac.
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
          <SettingRow label="Local model" info="The translation model that runs on this Mac. Chosen per language under Models.">
            <span className="muted">
              {short(s.localModel.name)}
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

        <SettingRow label="Try it" info="Translates a sample sentence with the service you chose.">
          <span aria-live="polite" className={test.error ? 'error' : 'muted'}>
            {test.ok && <strong>{test.ok.translation}</strong>}
            {test.error}
          </span>
          <button className="secondary" disabled={test.busy} onClick={runTest}>
            {test.busy ? 'Trying…' : 'Try it'}
          </button>
        </SettingRow>
      </SettingsGroup>

      {s.localModels.filter((m) => m.installed).length > 0 && (
        <SettingsGroup title="Compare local models">
          <p className="set-note muted">
            Translates one sentence with every model you have downloaded, so you can see which you like best. Nothing leaves this Mac. The first answer from a model includes loading it.
          </p>
          <SettingRow label="Language of the sentence">
            <select aria-label="Language of the sentence" value={compare.languageId ?? languages[0]?.id ?? ''} onChange={(e) => setCompare((c) => ({ ...c, languageId: Number(e.target.value) }))}>
              {languages.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name}
                </option>
              ))}
            </select>
          </SettingRow>
          <SettingRow label="Sentence">
            <textarea className="set-input" aria-label="Sentence" rows={3} value={compare.text} onChange={(e) => setCompare((c) => ({ ...c, text: e.target.value }))} />
          </SettingRow>
          <SettingRow label="">
            <button disabled={compare.busy || !compare.text.trim() || languages.length === 0} onClick={runCompare}>
              {compare.busy ? 'Translating…' : 'Compare'}
            </button>
          </SettingRow>
          <div aria-live="polite">
            {compare.error && <p className="error set-note">{compare.error}</p>}
            {compare.results?.map((r) => (
              <SettingRow key={r.id} label={r.name} info={`${r.seconds} s${r.cached ? ' · saved earlier' : ''}`}>
                <span className={r.error ? 'error' : undefined}>{r.error ?? r.translation}</span>
              </SettingRow>
            ))}
          </div>
        </SettingsGroup>
      )}
    </>
  )
}
