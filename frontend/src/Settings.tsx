import { useCallback, useEffect, useState } from 'react'
import { deleteModel, downloadModel, getJob, getModels, type Job, type Model } from './api'

function formatBytes(n: number): string {
  return n >= 1e9 ? `${(n / 1e9).toFixed(1)} GB` : `${Math.round(n / 1e6)} MB`
}

export function Settings() {
  const [models, setModels] = useState<Model[] | null>(null)
  const [job, setJob] = useState<Job | null>(null)
  const [error, setError] = useState('')

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

  const jobId = job?.state === 'running' ? job.id : null
  useEffect(() => {
    if (!jobId) return
    const timer = setInterval(async () => {
      const j = await getJob(jobId)
      setJob(j)
      if (j.state !== 'running') load()
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
  const busy = job?.state === 'running'
  return (
    <>
      <h1>Settings</h1>
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
                  {m.installed ? (
                    <>
                      <span className="muted">Installed</span>
                      <button className="secondary" disabled={busy} onClick={() => remove(m)}>
                        Delete
                      </button>
                    </>
                  ) : (
                    <button disabled={busy} onClick={() => download(m.id)}>
                      Download
                    </button>
                  )}
                </div>
              </div>
              {downloading && job && (
                <div className="progress">
                  <progress value={job.done} max={job.total || 1} />
                  <span className="muted">
                    {formatBytes(job.done)} / {formatBytes(job.total)}
                  </span>
                </div>
              )}
              {job?.state === 'error' && job.id === m.downloadJob && <p className="error">{job.error}</p>}
            </li>
          )
        })}
      </ul>
    </>
  )
}
