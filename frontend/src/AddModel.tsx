import { useEffect, useState } from 'react'
import { useOffline } from './offline'
import { addCustomModel, getEngines, lookupModel, type HubLookup } from './api'
import { notify } from './notices'
import { SPEECH_LANGUAGES } from './speechLanguages'

const size = (n: number) => (n >= 1e9 ? `${(n / 1e9).toFixed(1)} GB` : `${Math.round(n / 1e6)} MB`)

// Adds a model from Hugging Face to the list. It still has to be downloaded afterwards.
export function AddModel({ onAdded }: { onAdded: () => void }) {
  const offline = useOffline()
  const [engines, setEngines] = useState<{ id: string; name: string }[]>([])
  const [repo, setRepo] = useState('')
  const [name, setName] = useState('')
  const [engine, setEngine] = useState('')
  const [languages, setLanguages] = useState<string[]>(['nl', 'pl', 'fr'])
  const [found, setFound] = useState<HubLookup | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    getEngines().then(
      (e) => {
        setEngines(e.engines)
        setEngine((cur) => cur || e.engines[0]?.id || '')
      },
      () => undefined,
    )
  }, [])

  async function look() {
    setError('')
    setFound(null)
    setBusy(true)
    try {
      setFound(await lookupModel(repo.trim()))
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function add() {
    setError('')
    setBusy(true)
    try {
      const m = await addCustomModel({ repo: repo.trim(), engine, languages, name })
      notify(`${m.name} added. Download it to use it.`)
      setRepo('')
      setName('')
      setFound(null)
      onAdded()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const toggle = (code: string) =>
    setLanguages((cur) => (cur.includes(code) ? cur.filter((c) => c !== code) : [...cur, code]))

  return (
    <section className="set-group">
      <details className="set-card add-model-details">
        <summary>Add a model from Hugging Face…</summary>
        <div className="add-model-body">
      <p className="muted">
        Any Hugging Face model that works with one of the styles below: a voice, or a chat model that translates sentences. The app looks up its files, remembers the exact version, and downloads
        it like the others. A model of another kind won't load.
      </p>
      <div className="form add-model">
        <label>
          Repository (owner/name)
          <span className="row-inline">
            <input value={repo} placeholder="e.g. nativ-community/Audio8-TTS-Realistic-0.6b-8bit" onChange={(e) => (setRepo(e.target.value), setFound(null))} />
            <button className="secondary" disabled={busy || offline || !repo.trim()} onClick={look} title={offline ? 'Needs the internet (Work offline is on)' : undefined}>
              Look up
            </button>
          </span>
        </label>
        {found && (
          <>
            <p className="muted">
              {found.files} files · {size(found.totalBytes)} · license: {found.license}
              {found.modelType && <> · type: {found.modelType}</>}
              {(found.support.known === true || found.support.text?.known === true) && <> · recognised by Ocarina ✓</>}
              {found.support.known === false && found.support.text?.known !== true && <> · not recognised ✗</>}
            </p>
            <ul className="lookup-notes">
              {found.notes.map((n, i) => (
                <li key={i} className="muted">
                  {n}
                </li>
              ))}
            </ul>
            <label>
              Name (optional)
              <input value={name} onChange={(e) => setName(e.target.value)} />
            </label>
            <label>
              How it is used
              <select value={engine} onChange={(e) => setEngine(e.target.value)}>
                {engines.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.name}
                  </option>
                ))}
              </select>
            </label>
            <div className="status-row">
              {Object.entries(SPEECH_LANGUAGES).map(([code, label]) => (
                <label key={code} className="inline">
                  <input type="checkbox" checked={languages.includes(code)} onChange={() => toggle(code)} /> {label}
                </label>
              ))}
            </div>
            <div>
              <button disabled={busy || languages.length === 0} onClick={add}>
                Add to the list
              </button>
            </div>
          </>
        )}
        {error && <p className="error">{error}</p>}
      </div>
        </div>
      </details>
    </section>
  )
}
