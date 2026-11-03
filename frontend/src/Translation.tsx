import { useEffect, useState } from 'react'
import { getTranslateSettings, putTranslateSettings, testTranslation, type TranslateSettings, type Translation as Result } from './api'
import { notify } from './notices'

export function Translation() {
  const [s, setS] = useState<TranslateSettings | null>(null)
  const [email, setEmail] = useState('')
  const [key, setKey] = useState('')
  const [error, setError] = useState('')
  const [test, setTest] = useState<{ busy: boolean; ok?: Result; error?: string }>({ busy: false })

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
      <p>
        <a href="#/settings">← Settings</a>
      </p>
      <h1>Sentence translation</h1>
      <p className="muted">
        When you press “Translate sentence” in the reader, that sentence is sent to the service you choose here. Nothing is sent unless you press it, and
        translations you have seen are saved on this Mac.
      </p>

      <fieldset className="choices">
        <legend>Service</legend>
        {s.providers.map((p) => (
          <label key={p.id} className="choice">
            <input type="radio" name="provider" checked={s.provider === p.id} onChange={() => save({ provider: p.id })} />
            <span>
              <strong>{p.name}</strong>
              <span className="muted"> {p.description}</span>
            </span>
          </label>
        ))}
      </fieldset>

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
    </>
  )
}
