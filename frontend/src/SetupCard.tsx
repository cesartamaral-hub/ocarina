import { useCallback, useEffect, useState } from 'react'
import { downloadModel, getModels, getPref, setPref, type Model } from './api'
import { formatBytes } from './format'
import { useOffline } from './offline'
import { purposeOf } from './modelPurpose'

// On the Books screen while a starter model (voice, translation) is missing: what is missing, what is downloading, what failed (with Retry).
export function SetupCard() {
  const [models, setModels] = useState<Model[] | null>(null)
  const [hidden, setHidden] = useState(() => getPref<boolean>('setup.hidden', false))
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const offline = useOffline()
  const load = useCallback(() => getModels().then(setModels, () => undefined), [])
  useEffect(() => {
    load()
    const timer = window.setInterval(load, 3000)
    return () => window.clearInterval(timer)
  }, [load])

  const missing = (models ?? []).filter((m) => m.starter && !m.installed)
  const failed = missing.filter((m) => m.downloadError && !m.downloadJob)
  if (missing.length === 0 || (hidden && failed.length === 0)) return null
  const idle = missing.filter((m) => !m.downloadJob)
  const total = idle.reduce((n, m) => n + m.sizeBytes, 0)

  async function start() {
    setError('')
    setBusy(true)
    try {
      for (const m of idle) await downloadModel(m.id)
      await load()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="card setup-card" aria-label="Finish setting up">
      <h2>Finish setting up</h2>
      <p className="muted">Reading works already. These models add listening and translation, and run locally.</p>
      <ul className="starter-models">
        {missing.map((m) => (
          <li key={m.id}>
            {m.name} <span className="muted">· {formatBytes(m.sizeBytes)} · for {purposeOf(m).charAt(0).toLowerCase() + purposeOf(m).slice(1)}</span>
            {m.downloadJob && <div className="muted">Downloading…</div>}
            {m.downloadError && !m.downloadJob && <div className="error">The download failed: {m.downloadError}</div>}
          </li>
        ))}
      </ul>
      {offline && <p className="muted">Work offline is on, so nothing can be downloaded now (Settings → General).</p>}
      {error && <p className="error">{error}</p>}
      <p>
        {idle.length > 0 && (
          <button disabled={busy || offline} onClick={start}>
            {failed.length > 0 ? 'Try again' : `Download ${formatBytes(total)}`}
          </button>
        )}{' '}
        <a href="#/settings/models">All models</a>{' '}
        {failed.length === 0 && (
          <button
            className="secondary"
            onClick={() => {
              setPref('setup.hidden', true)
              setHidden(true)
            }}
          >
            Not now
          </button>
        )}
      </p>
    </section>
  )
}
