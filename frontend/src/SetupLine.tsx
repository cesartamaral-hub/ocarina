import { useCallback, useEffect, useState } from 'react'
import { downloadModel, getLanguageSupport, getModels, getPref, setPref, type Model } from './api'
import { DownloadStatus } from './DownloadStatus'
import { formatBytes } from './format'
import { featureOf } from './modelPurpose'
import { useOffline } from './offline'
import { relevantModels } from './welcomeModels'

// A slim line in the footer of the Books page while a recommended download (offline translation) is missing and could help the languages you
// study: what is missing and how big it is, Download and Not now; while it downloads its progress; if it failed, why and Try again.
// "Not now" hides it until something fails. It is not shown offline, when nothing can be downloaded.
export function SetupLine() {
  const [models, setModels] = useState<Model[] | null>(null)
  const [codes, setCodes] = useState<string[] | null>(null)
  const [hidden, setHidden] = useState(() => getPref<boolean>('setup.hidden', false))
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const offline = useOffline()
  const load = useCallback(() => getModels().then(setModels, () => undefined), [])
  useEffect(() => {
    load()
    getLanguageSupport().then((rows) => setCodes(rows.map((r) => r.code).filter((c): c is string => Boolean(c))), () => setCodes([]))
    const timer = window.setInterval(load, 3000)
    return () => window.clearInterval(timer)
  }, [load])

  const missing = codes === null ? [] : relevantModels(models ?? [], codes).filter((m) => m.starter && !m.installed) // the best translation model for your languages, unless you have one
  const failed = missing.filter((m) => m.downloadError && !m.downloadJob)
  const going = missing.filter((m) => m.downloadJob)
  if (offline || codes === null || missing.length === 0 || (hidden && failed.length === 0)) return null
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
    <aside className="setup-line" role="status" aria-label="Finish setting up">
      <span className="setup-text">
        {missing.length === 1 ? featureOf(missing[0]).missing : `${missing.length} downloads are not set up yet`}
        {going.length === 0 && ` · ${formatBytes(total)}`}
      </span>
      {going.map((m) => (
        <DownloadStatus key={m.id} model={m} onRetry={start} />
      ))}
      {failed.map((m) => (
        <span key={m.id} className="error setup-error">
          The download failed: {m.downloadError}
        </span>
      ))}
      {error && <span className="error setup-error">{error}</span>}
      <span className="setup-actions">
        {idle.length > 0 && (
          <button className="secondary small" disabled={busy} onClick={start}>
            {failed.length > 0 ? 'Try again' : 'Download'}
          </button>
        )}
        {failed.length === 0 && going.length === 0 && (
          <button
            className="quiet small"
            onClick={() => {
              setPref('setup.hidden', true)
              setHidden(true)
            }}
          >
            Not now
          </button>
        )}
      </span>
    </aside>
  )
}
