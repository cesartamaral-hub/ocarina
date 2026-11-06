import { useEffect, useState } from 'react'
import { getJob, type Job, type Model } from './api'
import { formatBytes, percent } from './format'

// One model's download as Welcome shows it: waiting, a percentage, installed, or why it failed (with a way to try again).
export function DownloadStatus({ model, onRetry }: { model: Model; onRetry: () => void }) {
  const [job, setJob] = useState<Job | null>(null)
  const jobId = model.downloadJob
  useEffect(() => {
    if (!jobId) return
    const timer = window.setInterval(() => getJob(jobId).then(setJob, () => undefined), 1000)
    return () => window.clearInterval(timer)
  }, [jobId])
  if (model.installed) return <span className="ready-ok">✓ installed</span>
  if (model.downloadError && !jobId) {
    return (
      <span className="error">
        Failed: {model.downloadError}{' '}
        <button className="secondary" onClick={onRetry}>
          Try again
        </button>
      </span>
    )
  }
  if (!jobId) return <span className="muted">Waiting…</span>
  if (!job || job.state === 'queued') return <span className="muted">Waiting for its turn…</span>
  return (
    <span className="muted">
      Downloading {formatBytes(job.done)} of {formatBytes(job.total)} ({percent(job.done, job.total)}%)
    </span>
  )
}
