import { useEffect, useState } from 'react'
import { downloadUpdate, getUpdate, installUpdate, skipUpdate, updateLater, type UpdateStatus } from './api'
import { formatBytes } from './format'

// At the top of the window when a newer Ocarina has been released: update now, remind me tomorrow, or skip this version.
export function UpdateBanner() {
  const [status, setStatus] = useState<UpdateStatus | null>(null)
  const [hidden, setHidden] = useState(false)
  const [error, setError] = useState('')
  const [restarting, setRestarting] = useState(false)

  useEffect(() => {
    getUpdate().then(setStatus, () => undefined) // once each time Ocarina starts
  }, [])

  const downloading = status?.download.state === 'running'
  useEffect(() => {
    if (!downloading) return
    const timer = window.setInterval(() => getUpdate().then(setStatus, () => undefined), 700)
    return () => window.clearInterval(timer)
  }, [downloading])

  if (!status || !status.show || !status.latest || hidden) return null
  const { latest, download } = status
  const ready = download.state === 'done' && download.version === latest.version
  const pct = download.total > 0 ? Math.min(100, Math.round((download.done / download.total) * 100)) : 0

  const run = (work: () => Promise<unknown>) => {
    setError('')
    work().catch((e: Error) => setError(e.message))
  }

  if (restarting) return <div className="update-banner">Updating to Ocarina {latest.version}… the app restarts by itself.</div>

  return (
    <div className="update-banner" role="status">
      <span>
        <strong>Ocarina {latest.version}</strong> is available (you have {status.current}).{' '}
        <a href={latest.url} target="_blank" rel="noreferrer">
          What is new
        </a>
        {error && <span className="error"> {error}</span>}
        {download.state === 'error' && <span className="error"> {download.error}</span>}
        {!status.canInstall && <span className="muted"> This copy cannot update itself: download the new version from the release page.</span>}
      </span>
      <span className="update-actions">
        {downloading ? (
          <span>Downloading… {pct}%</span>
        ) : ready ? (
          <button
            onClick={() =>
              run(async () => {
                await installUpdate()
                setRestarting(true)
              })
            }
          >
            Restart to update
          </button>
        ) : (
          status.canInstall && (
            <button onClick={() => run(() => downloadUpdate().then(() => getUpdate().then(setStatus)))}>
              Update now{latest.size ? ` (${formatBytes(latest.size)})` : ''}
            </button>
          )
        )}
        <button className="secondary" disabled={downloading} onClick={() => run(() => updateLater().then(() => setHidden(true)))}>
          Remind me tomorrow
        </button>
        <button className="secondary" disabled={downloading} onClick={() => run(() => skipUpdate(latest.version).then(() => setHidden(true)))}>
          Skip this version
        </button>
      </span>
    </div>
  )
}
