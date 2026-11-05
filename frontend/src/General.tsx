import { useEffect, useState } from 'react'
import { getOffline, type Readiness } from './api'
import { HoverSettings } from './HoverSettings'
import { UpdateSettings } from './UpdateSettings'
import { setOffline, useOffline } from './offline'

const Mark = ({ ok, names }: { ok: boolean; names: string[] }) =>
  ok ? (
    <span className="ready-ok" title={names.join(', ')}>
      ✓
    </span>
  ) : (
    <span className="ready-missing">missing</span>
  )

// The settings that are about the app as a whole: working without the internet, and how pointing at a word behaves.
export function General() {
  const offline = useOffline()
  const [ready, setReady] = useState<Readiness | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    getOffline().then(setReady, (e) => setError(e.message))
  }, [offline])
  return (
    <>
      <h1>General</h1>
      {error && <p className="error">{error}</p>}

      <section className="ap-card general-card">
        <h2>Work offline</h2>
        <label className="ap-check">
          <input type="checkbox" checked={offline} onChange={(e) => setOffline(e.target.checked)} />
          Use only what is on this Mac, and never the internet
        </label>
        <p className="muted ap-note">
          Meanings come from the dictionaries on this Mac, translation and speech from the models on this Mac, and nothing is downloaded. Adding a text from a web address or a YouTube video, playing a
          video in the reader, and the online translation and pronunciation services are not available. Files, pasted text and your own recordings work as always.
        </p>
        {ready && ready.languages.length > 0 && (
          <>
            <h3 className="general-sub">Is everything here for your languages?</h3>
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
              Audio sync for your own recordings: <Mark {...ready.audioSync} names={[ready.audioSync.name]} />. What is missing can be downloaded while the switch is off: dictionaries under{' '}
              <a href="#/settings/dictionaries">Dictionaries</a>, models under <a href="#/settings/models">Models</a>.
            </p>
          </>
        )}
      </section>

      <HoverSettings />
      <UpdateSettings />
    </>
  )
}
