import { useCallback, useEffect, useState } from 'react'
import { clearStorage, deleteModel, getStorage, type Storage as StorageInfo } from './api'
import { formatBytes } from './format'
import { notify } from './notices'

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
  const used = info.modelsBytes + info.dataBytes
  const KIND: Record<string, string> = Object.fromEntries(info.groups.map((g) => [g.kind, g.label.replace(/ models?$/, '')]))
  const models = [...info.models].sort((x, y) => y.bytes - x.bytes)
  const data = [...info.data].sort((x, y) => y.bytes - x.bytes)
  return (
    <>
      <h1>Storage</h1>
      <p className="sg-total">
        Ocarina uses <strong>{formatBytes(used)}</strong>
        {info.freeBytes !== null && <span className="muted"> · {formatBytes(info.freeBytes)} free on this disk</span>}
      </p>
      <div className="sg-bar" role="img" aria-label={`Models ${formatBytes(info.modelsBytes)}, your data ${formatBytes(info.dataBytes)}`}>
        <i className="models" style={{ width: `${(100 * info.modelsBytes) / Math.max(used, 1)}%` }} />
        <i className="data" style={{ width: `${(100 * info.dataBytes) / Math.max(used, 1)}%` }} />
      </div>
      <p className="sg-key muted">
        <span>
          <i className="models" /> Models {formatBytes(info.modelsBytes)}
        </span>
        <span>
          <i className="data" /> Your data {formatBytes(info.dataBytes)}
        </span>
      </p>
      {error && <p className="error">{error}</p>}

      <section className="sg-section" aria-labelledby="sg-models">
        <h2 id="sg-models">Models</h2>
        {models.length === 0 ? (
          <p className="muted">
            None downloaded. <a href="#/settings/models">Download one under Models</a>.
          </p>
        ) : (
          <ul className="sg-rows">
            {models.map((m) => (
              <li key={m.id}>
                <span className="sg-name">
                  <strong>{m.name}</strong>
                  <span className="muted">
                    {KIND[m.kind]}
                    {!m.installed && ' · download not finished'}
                  </span>
                </span>
                <span className="sg-size">{formatBytes(m.bytes)}</span>
                <button className="quiet small icon sg-bin" aria-label={`Delete ${m.name}`} title={`Delete (frees ${formatBytes(m.bytes)})`} onClick={() => remove(m.id, m.name, m.bytes)}>
                  <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
                    <path d="M3.5 4.5h9M6.5 4.5V3h3v1.5M5 4.5l.5 8h5l.5-8M7 7v3.5M9 7v3.5" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
              </li>
            ))}
            {info.leftoverBytes >= 1e6 && (
              <li className="sg-extra">
                <span className="sg-name">
                  <strong>Left over from models you deleted</strong>
                  <span className="muted">Pieces nothing uses any more</span>
                </span>
                <span className="sg-size">{formatBytes(info.leftoverBytes)}</span>
                <button className="secondary small" onClick={() => clear('leftovers', 'Leftovers from deleted models')}>
                  Free it
                </button>
              </li>
            )}
          </ul>
        )}
        {info.otherHubBytes > 0 && (
          <p className="muted sg-foot">
            {formatBytes(info.otherHubBytes)} more in the same folder (<code>{info.hubPath}</code>) belongs to other programs. Ocarina never deletes it.
          </p>
        )}
      </section>

      <section className="sg-section" aria-labelledby="sg-data">
        <h2 id="sg-data">Your data</h2>
        <ul className="sg-rows">
          {data.map((d) => (
            <li key={d.id}>
              <span className="sg-name">
                <strong>{d.label}</strong>
                <span className="muted">{d.description}</span>
              </span>
              <span className="sg-size">{formatBytes(d.bytes)}</span>
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
      </section>
    </>
  )
}
