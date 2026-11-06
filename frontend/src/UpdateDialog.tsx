import { useEffect, useRef, useState } from 'react'
import { downloadUpdate, getUpdate, installUpdate, skipUpdate, updateLater } from './api'
import { parseNotes } from './changelog'
import { useEscape } from './escape'
import { formatBytes } from './format'
import { dismissUpdate, loadUpdate, setUpdateStatus, useUpdate } from './updateStore'

// A window that opens when a newer Ocarina has been released: what changed (scrolls when long), a link to the release on GitHub,
// and at the bottom Skip this version, Remind me later and Install. Esc closes it for now without choosing.
export function UpdateDialog() {
  const { status, dismissed, forced } = useUpdate()
  const [error, setError] = useState('')
  const [restarting, setRestarting] = useState(false)
  const dialog = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    loadUpdate() // once each time Ocarina starts
  }, [])

  const downloading = status?.download.state === 'running'
  useEffect(() => {
    if (!downloading) return
    const timer = window.setInterval(() => getUpdate().then(setUpdateStatus, () => undefined), 700)
    return () => window.clearInterval(timer)
  }, [downloading])

  const open = Boolean(status?.latest && !dismissed && (forced || status.show))
  useEscape(open, dismissUpdate) // the window's own Esc handler would otherwise swallow the key
  useEffect(() => {
    const el = dialog.current
    if (open && el && !el.open) el.showModal()
  }, [open])

  if (!status || !open || !status.latest) return null
  const { latest, download } = status
  const ready = download.state === 'done' && download.version === latest.version
  const pct = download.total > 0 ? Math.min(100, Math.round((download.done / download.total) * 100)) : 0
  const notes = parseNotes(latest.notes)

  const run = (work: () => Promise<unknown>) => {
    setError('')
    work().catch((e: Error) => setError(e.message))
  }

  return (
    <dialog ref={dialog} className="update-dialog" aria-labelledby="update-title" onCancel={dismissUpdate}>
      {restarting ? (
        <div className="ud-body">
          <h2 id="update-title">Updating to Ocarina {latest.version}</h2>
          <p className="muted">The app restarts by itself in a moment.</p>
        </div>
      ) : (
        <>
          <header className="ud-head">
            <h2 id="update-title">Ocarina {latest.version} is available</h2>
            <p className="muted">
              You have {status.current}
              {latest.size ? ` · ${formatBytes(latest.size)} to download` : ''}
            </p>
          </header>
          <div className="ud-notes" tabIndex={0} aria-label="What is new">
            {notes.length === 0 ? (
              <p className="muted">No release notes were written for this version.</p>
            ) : (
              notes.map((b, i) =>
                b.type === 'heading' ? (
                  <h3 key={i}>{b.text}</h3>
                ) : b.type === 'item' ? (
                  <p key={i} className="ud-item">
                    {b.text}
                  </p>
                ) : (
                  <p key={i}>{b.text}</p>
                ),
              )
            )}
          </div>
          <p className="ud-more">
            <a href={latest.url} target="_blank" rel="noreferrer">
              See this release on GitHub
            </a>
          </p>
          {error && <p className="error ud-msg">{error}</p>}
          {download.state === 'error' && <p className="error ud-msg">{download.error}</p>}
          {!status.canInstall && <p className="muted ud-msg">This copy cannot update itself: download the new version from the release page.</p>}
          {downloading && (
            <div className="ud-progress">
              <progress value={download.done} max={download.total || 1} aria-label="Downloading the update" />
              <span className="muted">Downloading… {pct}%</span>
            </div>
          )}
          <footer className="ud-foot">
            <span className="ud-later">
              <button className="quiet" disabled={downloading} onClick={() => run(() => skipUpdate(latest.version).then(dismissUpdate))}>
                Skip this version
              </button>
              <button className="secondary" disabled={downloading} onClick={() => run(() => updateLater().then(dismissUpdate))}>
                Remind me later
              </button>
            </span>
            {ready ? (
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
            ) : status.canInstall ? (
              <button disabled={downloading} onClick={() => run(() => downloadUpdate().then(() => getUpdate().then(setUpdateStatus)))}>
                {downloading ? 'Downloading…' : 'Install update'}
              </button>
            ) : (
              <a className="button" href={latest.url} target="_blank" rel="noreferrer">
                Open the release page
              </a>
            )}
          </footer>
        </>
      )}
    </dialog>
  )
}
