import { useCallback, useEffect, useState } from 'react'
import { clearStorage, deleteModel, getStorage, type Storage as StorageInfo, type StorageGroup } from './api'
import { formatBytes } from './format'
import { notify } from './notices'

const GROUP_CLASS: Record<StorageGroup['kind'], string> = { speech: 'g-voice', text: 'g-text', aligner: 'g-sync' }

// How much disk space the models and Ocarina's data take, and what can be freed.
export function Storage() {
  const [info, setInfo] = useState<StorageInfo | null>(null)
  const [error, setError] = useState('')

  const load = useCallback(() => getStorage().then(setInfo, (e) => setError(e.message)), [])
  useEffect(() => {
    load()
  }, [load])

  async function remove(id: string, name: string, bytes: number) {
    if (!window.confirm(`Delete ${name} (${formatBytes(bytes)})? You can download it again in Settings.`)) return
    setError('')
    try {
      await deleteModel(id)
      notify(`${name} deleted`)
      load()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  async function clear(what: string, label: string) {
    if (!window.confirm(`Clear “${label}”? Nothing you made yourself is affected.`)) return
    setError('')
    try {
      const done = await clearStorage(what)
      setInfo(done)
      notify(`${formatBytes(done.freed)} freed`)
    } catch (e) {
      setError((e as Error).message)
    }
  }

  if (!info) return error ? <p className="error">{error}</p> : <p className="muted">Loading…</p>
  const total = Math.max(info.modelsBytes, 1)
  return (
    <>
      <p>
        <a href="#/settings">← Settings</a>
      </p>
      <h1>Storage</h1>
      <p className="muted">
        What Ocarina keeps on this Mac.
        {info.freeBytes !== null && <> {formatBytes(info.freeBytes)} is free on this disk.</>}
      </p>
      {error && <p className="error">{error}</p>}

      <h2>Models · {formatBytes(info.modelsBytes)}</h2>
      {info.modelsBytes > 0 && (
        <>
          <div className="storage-bar" role="img" aria-label={info.groups.map((g) => `${g.label} ${formatBytes(g.bytes)}`).join(', ')}>
            {info.groups
              .filter((g) => g.bytes > 0)
              .map((g) => (
                <i key={g.kind} className={GROUP_CLASS[g.kind]} style={{ width: `${(100 * g.bytes) / total}%` }} />
              ))}
          </div>
          <ul className="storage-legend">
            {info.groups.map((g) => (
              <li key={g.kind}>
                <i className={GROUP_CLASS[g.kind]} /> {g.label} <strong>{formatBytes(g.bytes)}</strong>
              </li>
            ))}
          </ul>
        </>
      )}
      {info.groups.map((g) => {
        const rows = info.models.filter((m) => m.kind === g.kind)
        return (
          <section key={g.kind} className="storage-group">
            <h3>
              <i className={GROUP_CLASS[g.kind]} /> {g.label} <span className="muted">{formatBytes(g.bytes)}</span>
            </h3>
            {rows.length === 0 ? (
              <p className="muted">None downloaded. <a href="#/settings">Download one in Settings</a>.</p>
            ) : (
              <ul className="storage-rows">
                {rows.map((m) => (
                  <li key={m.id}>
                    <span>
                      <strong>{m.name}</strong>
                      {!m.installed && <span className="muted"> · download not finished</span>}
                    </span>
                    <span className="storage-size">{formatBytes(m.bytes)}</span>
                    <button className="danger small" onClick={() => remove(m.id, m.name, m.bytes)}>
                      Delete
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        )
      })}
      {info.leftoverBytes >= 1e6 && (
        <p className="storage-note">
          <strong>{formatBytes(info.leftoverBytes)}</strong> is left over from models that were deleted earlier.{' '}
          <button className="secondary small" onClick={() => clear('leftovers', 'Leftovers from deleted models')}>
            Free it
          </button>
        </p>
      )}
      {info.otherHubBytes > 0 && (
        <p className="muted">
          Another {formatBytes(info.otherHubBytes)} in the same folder (<code>{info.hubPath}</code>) belongs to other models, for example ones you used
          with other programs. Ocarina never deletes those.
        </p>
      )}

      <h2>Your data · {formatBytes(info.dataBytes)}</h2>
      <ul className="storage-rows">
        {info.data.map((d) => (
          <li key={d.id}>
            <span>
              <strong>{d.label}</strong>
              <span className="muted"> {d.description}</span>
            </span>
            <span className="storage-size">{formatBytes(d.bytes)}</span>
            {d.clearable ? (
              <button className="secondary small" disabled={d.bytes === 0} onClick={() => clear(d.id, d.label)}>
                Clear
              </button>
            ) : (
              <span />
            )}
          </li>
        ))}
      </ul>
    </>
  )
}
