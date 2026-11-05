import { useEffect, useState } from 'react'
import { compareModels, getLanguages, getTranslateSettings, putTranslateSettings, testTranslation, type Comparison, type Language, type TranslateSettings, type Translation as Result } from './api'
import { formatBytes } from './format'
import { notify } from './notices'
import { SPEECH_LANGUAGES } from './speechLanguages'

export function Translation() {
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
  return (
    <>
      <h1>Sentence translation</h1>
      <p className="muted">
        When you press “Translate sentence” in the reader, that sentence is sent to the service you choose here. Nothing is sent unless you press it, and
        translations you have seen are saved on this Mac.
      </p>

      <fieldset className="choices">
        <legend>Service</legend>
        {s.providers.map((p) => {
          const missing = p.id === 'local' && !s.localModel.installed
          return (
            <label key={p.id} className={`choice${missing ? ' unavailable' : ''}`}>
              <input type="radio" name="provider" disabled={missing} checked={s.provider === p.id} onChange={() => save({ provider: p.id })} />
              <span>
                <strong>{p.name}</strong>
                <span className="muted"> {p.description}</span>
                {missing && (
                  <span className="choice-note">
                    {' '}
                    Not downloaded yet ({formatBytes(s.localModel.sizeBytes)}). <a href="#/settings/models">Download it in Settings</a>.
                  </span>
                )}
              </span>
            </label>
          )
        })}
      </fieldset>

      {s.provider === 'local' && (
        <p className="muted tr-model-line">
          On this Mac: <strong>{s.localModel.name.replace(/\s*\(.*\)\s*$/, '')}</strong>
          {Object.entries(s.localModelByLanguage ?? {}).map(([code, id]) => (
            <span key={code}>
              {' '}
              · {SPEECH_LANGUAGES[code] ?? code.toUpperCase()}: <strong>{(s.localModels.find((m) => m.id === id)?.name ?? id).replace(/\s*\(.*\)\s*$/, '')}</strong>
            </span>
          ))}{' '}
          · <a href="#/settings/models">change under Models</a>
        </p>
      )}

      <div className="form translation-form">
        <label>
          Translate into
          <select value={s.target} onChange={(e) => save({ target: e.target.value })}>
            {s.targets.map((t) => (
              <option key={t.code} value={t.code}>
                {t.name}
              </option>
            ))}
          </select>
        </label>

        {s.provider === 'mymemory' && (
          <label>
            Email address (optional)
            <span className="row-inline">
              <input type="email" value={email} placeholder="you@example.com" onChange={(e) => setEmail(e.target.value)} />
              <button className="secondary" disabled={email === s.email} onClick={() => save({ email }, 'Saved')}>
                Save
              </button>
            </span>
            <span className="muted">MyMemory allows ten times more translations a day when it knows an address. It is used for that and nothing else.</span>
          </label>
        )}

        {s.provider === 'deepl' && (
          <label>
            DeepL API key
            {s.hasDeeplKey ? (
              <span className="row-inline">
                <span>
                  A key is saved <span className="muted">({s.deeplKeyHint})</span>
                </span>
                <button className="secondary" onClick={() => save({ deeplKey: '' }, 'Key removed')}>
                  Remove
                </button>
              </span>
            ) : (
              <span className="row-inline">
                <input type="password" autoComplete="off" value={key} placeholder="Paste your key" onChange={(e) => setKey(e.target.value)} />
                <button
                  disabled={!key.trim()}
                  onClick={() => {
                    save({ deeplKey: key }, 'Key saved')
                    setKey('')
                  }}
                >
                  Save key
                </button>
              </span>
            )}
            <span className="muted">
              Get a free key at deepl.com (“DeepL API Free”). It is kept in a private file in the Ocarina data folder, and never shown again.
            </span>
          </label>
        )}

        <div className="actions">
          <button className="secondary" disabled={test.busy} onClick={runTest}>
            {test.busy ? 'Trying…' : 'Try it'}
          </button>
        </div>
        <div aria-live="polite">
          {test.ok && (
            <p>
              “Goedemorgen, hoe gaat het met je?” → <strong>{test.ok.translation}</strong>
            </p>
          )}
          {test.error && <p className="error">{test.error}</p>}
        </div>
        {error && <p className="error">{error}</p>}
      </div>

      {s.localModels.filter((m) => m.installed).length > 0 && (
        <section className="compare">
          <h2>Compare the models on this Mac</h2>
          <p className="muted">
            Translates one sentence with every model you have downloaded, so you can see which you like best. Nothing leaves this Mac. The first answer from a model includes
            loading it.
          </p>
          <div className="form">
            <label>
              Language of the sentence
              <select value={compare.languageId ?? languages[0]?.id ?? ''} onChange={(e) => setCompare((c) => ({ ...c, languageId: Number(e.target.value) }))}>
                {languages.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Sentence
              <textarea rows={3} value={compare.text} onChange={(e) => setCompare((c) => ({ ...c, text: e.target.value }))} />
            </label>
            <div className="actions">
              <button disabled={compare.busy || !compare.text.trim() || languages.length === 0} onClick={runCompare}>
                {compare.busy ? 'Translating…' : 'Compare'}
              </button>
            </div>
          </div>
          <div aria-live="polite">
            {compare.error && <p className="error">{compare.error}</p>}
            {compare.results && (
              <ul className="comparison">
                {compare.results.map((r) => (
                  <li key={r.id}>
                    <strong>{r.name}</strong>{' '}
                    <span className="muted">
                      {r.seconds} s{r.cached ? ' · saved earlier' : ''}
                    </span>
                    <p className={r.error ? 'error' : undefined}>{r.error ?? r.translation}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      )}
    </>
  )
}
