import { useEffect, useState } from 'react'
import { getOffline, type Readiness } from './api'
import { setOffline, useOffline } from './offline'
import { offlineSummary } from './offlineReadiness'
import { SettingRow, SettingsGroup, Toggle } from './SettingsKit'

const Mark = ({ ok, names }: { ok: boolean; names: string[] }) =>
  ok ? (
    <span className="ready-ok" title={names.join(', ')}>
      ✓
    </span>
  ) : (
    <span className="ready-missing">missing</span>
  )

// Work offline: one row with a switch, one line of status, and the per-language table folded away.
export function OfflineSetting() {
  const offline = useOffline()
  const [ready, setReady] = useState<Readiness | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    getOffline().then(setReady, (e) => setError(e.message))
  }, [offline])
  const summary = ready ? offlineSummary(ready) : null
  return (
    <SettingsGroup title="Connection">
      <SettingRow
        label="Work offline"
        info="Use only local dictionaries and models, so Ocarina keeps working without a connection. Web and YouTube imports, online translation and online pronunciation are paused; files, pasted text and your own recordings work as always."
      >
        <Toggle label="Work offline" checked={offline} onChange={setOffline} />
      </SettingRow>
      {error && <p className="error set-note">{error}</p>}
      {summary?.text && <p className={`offline-status set-note${summary.ok ? '' : ' warn'}`}>{summary.text}</p>}
      {ready && ready.languages.length > 0 && (
        <details className="offline-details set-note">
          <summary>Details by language</summary>
          <table className="ready-table">
            <thead>
              <tr>
                <th>Language</th>
                <th>Dictionary</th>
                <th>Translation</th>
                <th>Voice</th>
              </tr>
            </thead>
            <tbody>
              {ready.languages.map((l) => (
                <tr key={l.code}>
                  <th scope="row">{l.name}</th>
                  <td>
                    <Mark {...l.dictionary} />
                  </td>
                  <td>
                    <Mark {...l.translation} />
                  </td>
                  <td>
                    <Mark {...l.voice} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="muted ap-note">
            Audio sync for your own recordings: <Mark {...ready.audioSync} names={[ready.audioSync.name]} />. Get what is missing under <a href="#/settings/dictionaries">Dictionaries</a> or{' '}
            <a href="#/settings/models">Models</a> (downloads need the switch off).
          </p>
        </details>
      )}
    </SettingsGroup>
  )
}
