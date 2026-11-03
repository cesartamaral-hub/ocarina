import type { Job } from './api'
import { formatBytes, formatSpeed, formatTimeLeft, percent } from './format'

// Progress of a model download or import: a bar, what is done, and speed and time left once they are known.
export function TransferProgress({ job, speed, onCancel }: { job: Job; speed: number; onCancel: () => void }) {
  const waiting = job.state === 'queued'
  const starting = !waiting && job.done === 0
  const finishing = !waiting && job.total > 0 && job.done >= job.total
  const pct = percent(job.done, job.total)
  const left = speed > 0 && job.total > job.done ? formatTimeLeft((job.total - job.done) / speed) : ''
  const label = waiting
    ? job.queuePosition && job.queuePosition > 1
      ? `Waiting for ${job.queuePosition - 1} jobs before it…`
      : 'Waiting for the job before it…'
    : starting
      ? 'Starting…'
      : finishing
        ? 'Checking the files…'
        : `${formatBytes(job.done)} of ${formatBytes(job.total)} (${pct}%)`
  return (
    <div className="transfer" role="group" aria-label="Download progress">
      <div className="transfer-bar">
        {/* No value = an indeterminate bar, for the moments when nothing can be measured. */}
        <progress
          value={waiting || starting || finishing ? undefined : job.done}
          max={job.total || 1}
          aria-label={`${job.title ?? 'Model'} ${waiting || starting ? 'is starting' : `${pct} percent`}`}
        />
        <button className="secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
      <div className="transfer-text muted" aria-live="polite">
        <span>{label}</span>
        {!waiting && !starting && !finishing && speed > 0 && (
          <span>
            {formatSpeed(speed)}
            {left && ` · ${left}`}
          </span>
        )}
      </div>
    </div>
  )
}
