import { useEffect, useState } from 'react'
import { SettingRow, SettingsGroup, Toggle } from './SettingsKit'
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
  const apply = (patch: Partial<typeof form>) => {
    const next = { ...form, ...patch }
    setForm(next)
    run(() => saveBackupSettings(next), 'Saved.')
  }
  return (
    <>
      <h1>Backups</h1>
      {state.warning && (
        <p className="error">
          {state.warning}{' '}
          <button className="secondary" onClick={() => run(skipBackup, 'Reminder snoozed for today.')}>
            Not now
          </button>
        </p>
      )}
      {error && <p className="error">{error}</p>}

      <SettingsGroup title="Automatic backups">
        <SettingRow label="Back up my library" info="A backup is a compressed copy of your database (books, terms, statuses). Your images are copied next to it. Audio files are not included.">
          <Toggle label="Back up my library" checked={form.enabled} disabled={busy} onChange={(on) => apply({ enabled: on })} />
        </SettingRow>
        <SettingRow label="Once a day, when the app opens" disabled={!form.enabled}>
          <Toggle label="Back up automatically once a day" checked={form.auto} disabled={busy || !form.enabled} onChange={(on) => apply({ auto: on })} />
        </SettingRow>
        <SettingRow label="Remind me about old backups" info="Reminds you when the last backup is more than a week old." disabled={!form.enabled}>
          <Toggle label="Remind me about old backups" checked={form.warn} disabled={busy || !form.enabled} onChange={(on) => apply({ warn: on })} />
        </SettingRow>
        <SettingRow label="Automatic backups to keep" disabled={!form.enabled}>
          <input
            type="number"
            className="set-input narrow"
            aria-label="Automatic backups to keep"
            min={1}
            max={100}
            disabled={!form.enabled}
            value={form.count}
            onChange={(e) => setForm({ ...form, count: Number(e.target.value) })}
            onBlur={() => apply({})}
          />
        </SettingRow>
        <SettingRow label="Folder" info="A full path. Leave it as it is to keep backups in the Ocarina data folder.">
          <input className="set-input" aria-label="Backup folder" value={form.dir} onChange={(e) => setForm({ ...form, dir: e.target.value })} onBlur={() => apply({})} />
        </SettingRow>
        <SettingRow label="Last backup">
          <span className="muted">{note || when(state.settings.lastBackup)}</span>
          <button className="secondary" disabled={busy} onClick={() => run(() => makeBackup(true), 'Backup made.')}>
            Back up now
          </button>
        </SettingRow>
      </SettingsGroup>

      <SettingsGroup title="Backups in the folder">
        {state.backups.length === 0 ? (
          <p className="set-note muted">None yet.</p>
        ) : (
          state.backups.map((b) => (
            <SettingRow key={b.name} label={b.name}>
              <span className="muted">
                {when(b.modified)} · {b.size}
                {b.manual ? ' · kept for good' : ''}
              </span>
              <a href={backupDownloadUrl(b.name)} download>
                Download
              </a>
            </SettingRow>
          ))
        )}
        <p className="set-note muted">
          To restore one: quit Ocarina, unzip the file, and put it in the Ocarina data folder as <code>ocarina.db</code>.
        </p>
      </SettingsGroup>
    </>
  )
}
