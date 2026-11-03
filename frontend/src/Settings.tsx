import { useCallback, useEffect, useState } from 'react'
import {
  cancelJob,
  canPickFolder,
  deleteModel,
  downloadModel,
  getJob,
  getModels,
  getVoices,
  getPref,
  importModel,
  isActive,
  pickFolder,
  removeModelEntry,
  setPref,
  type Job,
  type Model,
  type Voice,
} from './api'
import { AddModel } from './AddModel'
import { SPEECH_LANGUAGES } from './speechLanguages'
import { Voices } from './Voices'

function formatBytes(n: number): string {
  return n >= 1e9 ? `${(n / 1e9).toFixed(1)} GB` : `${Math.round(n / 1e6)} MB`
}

export function Settings() {
  const [models, setModels] = useState<Model[] | null>(null)
  const [job, setJob] = useState<Job | null>(null)
  const [error, setError] = useState('')
  const [chosen, setChosen] = useState<Record<string, string>>({})
  const [voices, setVoices] = useState<Voice[]>([])
  const loadVoices = useCallback(() => getVoices().then(setVoices, () => undefined), [])
  useEffect(() => {
    loadVoices()
  }, [loadVoices])

  const load = useCallback(
    () =>
      getModels().then(
        (list) => {
          setModels(list)
          // A download started earlier (or in another window) keeps showing its progress.
          const active = list.find((m) => m.downloadJob)
          if (active?.downloadJob) getJob(active.downloadJob).then((j) => setJob((cur) => cur ?? j))
        },
        (e) => setError(e.message),
      ),
    [],
  )
  useEffect(() => {
    load()
  }, [load])

  const jobId = isActive(job) ? job!.id : null
  useEffect(() => {
    if (!jobId) return
    const timer = setInterval(async () => {
      const j = await getJob(jobId)
      setJob(j)
      if (!isActive(j)) load()
    }, 700)
    return () => clearInterval(timer)
  }, [jobId, load])

  async function download(id: string) {
    setError('')
    try {
      setJob(await downloadModel(id))
    } catch (e) {
      setError((e as Error).message)
    }
  }

  async function importFrom(m: Model) {
    setError('')
    try {
      // The desktop app has a native folder dialog; the browser used in development asks for a path.
      const folder = canPickFolder()
        ? await pickFolder()
        : window.prompt('Path of the folder with the downloaded model files')
      if (folder) setJob(await importModel(m.id, folder))
    } catch (e) {
      setError((e as Error).message)
    }
  }

  function choose(key: string, value: string) {
    setPref(key, value)
    setChosen((cur) => ({ ...cur, [key]: value }))
  }

  async function forget(m: Model) {
    if (!window.confirm(`Remove ${m.name} from the list? Its downloaded files are deleted too.`)) return
    setError('')
    try {
      await removeModelEntry(m.id)
      load()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  async function remove(m: Model) {
    if (!window.confirm(`Delete ${m.name} (${formatBytes(m.sizeBytes)})? You can download it again.`)) return
    setError('')
    try {
      await deleteModel(m.id)
      setJob(null)
      load()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  if (!models) return error ? <p className="error">{error}</p> : <p className="muted">Loading…</p>
  const busy = isActive(job)
  return (
    <>
      <h1>Settings</h1>
      <p className="settings-links">
        <a href="#/appearance">Appearance</a> · <a href="#/shortcuts">Keyboard shortcuts</a> · <a href="#/tags">Tags</a> ·{' '}
        <a href="#/languages">Languages</a> · <a href="#/backups">Backups</a>
      </p>
      <h2>Voice models</h2>
      <p className="muted">
        Models are downloaded once and run on this Mac. Audio generation needs one installed.
      </p>
      {error && <p className="error">{error}</p>}
      <ul className="models">
        {models.map((m) => {
          const downloading = busy && job?.id === m.downloadJob
          return (
            <li key={m.id}>
              <div className="row">
                <div>
                  <div className="name">{m.name}</div>
                  <div className="muted">{m.description}</div>
                  <div className="muted">
                    {m.languages.join(', ')} · {m.license.toUpperCase()} · {formatBytes(m.sizeBytes)}
                    {m.benchmark && ` · about ${m.benchmark.secondsPerSecondOfAudio}s per second of audio`}
                  </div>
                </div>
                <div className="actions">
                  {m.custom && (
                    <button className="secondary" disabled={busy} onClick={() => forget(m)}>
                      Remove from list
                    </button>
                  )}
                  {m.installed ? (
                    <>
                      <span className="muted">Installed</span>
                      <button className="secondary" disabled={busy} onClick={() => remove(m)}>
                        Delete
                      </button>
                    </>
                  ) : (
                    <>
                      <button className="secondary" disabled={busy} onClick={() => importFrom(m)}>
                        Import from folder…
                      </button>
                      <button disabled={busy} onClick={() => download(m.id)}>
                        Download
                      </button>
                    </>
                  )}
                </div>
              </div>
              {downloading && job && (
                <div className="progress">
                  <progress value={job.done} max={job.total || 1} />
                  <span className="muted">
                    {job.state === 'queued'
                      ? 'Waiting for the job before it…'
                      : `${formatBytes(job.done)} / ${formatBytes(job.total)}`}
                  </span>
                  <button className="secondary" onClick={() => cancelJob(job.id).then(setJob, () => undefined)}>
                    Cancel
                  </button>
                </div>
              )}
              {job?.state === 'error' && job.id === m.downloadJob && <p className="error">{job.error}</p>}
              {job?.state === 'cancelled' && job.model_id === m.id && (
                <p className="muted">Cancelled. Files already copied or downloaded are kept.</p>
              )}
            </li>
          )
        })}
      </ul>

      <AddModel onAdded={load} />

      <h2>Voice per language</h2>
      <p className="muted">Which installed model and which voice make the audio of books in each language.</p>
      <ul className="models">
        {Object.entries(SPEECH_LANGUAGES).map(([code, name]) => {
          const options = models.filter((m) => m.installed && m.languages.includes(code))
          const value = chosen[`model.${code}`] ?? getPref<string>(`model.${code}`, '')
          const voice = chosen[`voice.${code}`] ?? getPref<string>(`voice.${code}`, '')
          return (
            <li key={code}>
              <div className="row">
                <div className="name">{name}</div>
                <select value={value} onChange={(e) => choose(`model.${code}`, e.target.value)}>
                  <option value="">Automatic (first installed)</option>
                  {options.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name}
                    </option>
                  ))}
                </select>
                <select value={voice} onChange={(e) => choose(`voice.${code}`, e.target.value)} aria-label={`Voice for ${name}`}>
                  <option value="">Automatic</option>
                  {voices.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.name}
                    </option>
                  ))}
                </select>
              </div>
            </li>
          )
        })}
      </ul>
      <Voices voices={voices} onChange={loadVoices} />
    </>
  )
}
