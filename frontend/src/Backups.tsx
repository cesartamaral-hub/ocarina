import { useEffect, useState } from 'react'
import { backupDownloadUrl, getBackups, getBackupsAfterStartup, makeBackup, saveBackupSettings, skipBackup, type BackupState } from './api'

const when = (t: number | null) => (t ? new Date(t * 1000).toLocaleString() : 'never')

export function Backups() {
  const [state, setState] = useState<BackupState | null>(null)
  const [form, setForm] = useState({ enabled: true, auto: true, warn: true, dir: '', count: 5 })
  const [error, setError] = useState('')
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)

  function show(s: BackupState) {
    setState(s)
    setForm({ ...s.settings })
  }
  useEffect(() => {
    getBackupsAfterStartup().then(show, (e) => setError(e.message))
  }, [])

  async function run(work: () => Promise<unknown>, done: string) {
    setError('')
    setNote('')
    setBusy(true)
    try {
      await work()
      show(await getBackups())
      setNote(done)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  if (!state) return error ? <p className="error">{error}</p> : <p className="muted">Loading…</p>
  const set = (patch: Partial<typeof form>) => setForm({ ...form, ...patch })
  return (
    <>
      <p>
        <a href="#/settings">← Settings</a>
      </p>
      <h1>Backups</h1>
      <p className="muted">
        A backup is a compressed copy of your database (books, terms, statuses). Your images are copied next to it. Audio files are not included.
        Last backup: {when(state.settings.lastBackup)}.
      </p>
      {state.warning && (
        <p className="error">
          {state.warning}{' '}
          <button className="secondary" onClick={() => run(skipBackup, 'Reminder snoozed for today.')}>
            Not now
          </button>
        </p>
      )}

      <div className="form backup-form">
        <label className="inline">
          <input type="checkbox" checked={form.enabled} onChange={(e) => set({ enabled: e.target.checked })} />
          Back up my library
        </label>
        <label className="inline">
          <input type="checkbox" checked={form.auto} onChange={(e) => set({ auto: e.target.checked })} />
          Back up automatically once a day, when the app opens
        </label>
        <label className="inline">
          <input type="checkbox" checked={form.warn} onChange={(e) => set({ warn: e.target.checked })} />
          Remind me when the last backup is more than a week old
        </label>
        <label>
          Folder (a full path)
          <input value={form.dir} onChange={(e) => set({ dir: e.target.value })} />
        </label>
        <label>
          Automatic backups to keep
          <input type="number" min={1} max={100} value={form.count} onChange={(e) => set({ count: Number(e.target.value) })} />
        </label>
        <div className="actions">
          <button disabled={busy} onClick={() => run(() => saveBackupSettings(form), 'Settings saved.')}>
            Save settings
          </button>
          <button className="secondary" disabled={busy} onClick={() => run(() => makeBackup(true), 'Backup made.')}>
            Back up now
          </button>
        </div>
        {error && <p className="error">{error}</p>}
        {note && <p className="muted">{note}</p>}
      </div>

      <h2>Backups in the folder</h2>
      {state.backups.length === 0 ? (
        <p className="muted">None yet.</p>
      ) : (
        <ul className="books">
          {state.backups.map((b) => (
            <li key={b.name}>
              <a href={backupDownloadUrl(b.name)} download>
                {b.name}
              </a>
              <span className="muted">
                {when(b.modified)} · {b.size}
                {b.manual ? ' · kept for good' : ''}
              </span>
            </li>
          ))}
        </ul>
      )}
      <p className="muted">
        To restore one: quit Ocarina, unzip the file, and put it in the Ocarina data folder as <code>ocarina.db</code>.
      </p>
    </>
  )
}
