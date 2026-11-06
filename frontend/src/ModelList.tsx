import { useAnchoredPopover } from './useAnchoredPopover'
import { Popover } from './Popover'
import { formatBytes } from './format'
import { coverageNote, languageCount, speedLevel } from './modelRows'
import { TransferProgress } from './TransferProgress'
import { CheckResult } from './CheckResult'
import { cancelJob, getJob, isActive, type Job, type Model } from './api'
import { SPEECH_LANGUAGES } from './speechLanguages'

export type ModelActions = {
  busy: boolean
  offline?: boolean // Work offline is on: nothing can be downloaded
  job: Job | null
  speed: number
  codes: string[] // the languages you study, to say when a model leaves one out
  names?: Record<string, string> // a language's name by its code
  inUse: (m: Model) => boolean // whether the model is the one doing this job now
  onUse?: (m: Model) => void // makes it the model in use (when more than one can be)
  onDownload: (id: string) => void
  onImport: (m: Model) => void
  onTest: (m: Model) => void
  onDelete: (m: Model) => void
  onForget: (m: Model) => void
  onJob: (job: Job) => void
}

const BIN = (
  <path d="M3.5 4.5h9M6.5 4.5V3h3v1.5M5 4.5l.5 8h5l.5-8M7 7v3.5M9 7v3.5" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
)

function Menu({ m, a }: { m: Model; a: ModelActions }) {
  const { anchor, placement, toggle, close } = useAnchoredPopover(220, 'end')
  const item = (label: string, run: () => void) => (
    <li role="none">
      <button
        role="menuitem"
        disabled={a.busy}
        onClick={() => {
          close()
          run()
        }}
      >
        {label}
      </button>
    </li>
  )
  const entries = [m.installed && item(m.check ? 'Test again' : 'Test', () => a.onTest(m)), !m.installed && item('Import from a folder…', () => a.onImport(m)), m.custom && item('Remove from the list', () => a.onForget(m))].filter(Boolean)
  if (entries.length === 0) return null
  return (
    <>
      <button ref={anchor} className="quiet small icon mr-more" aria-label={`More for ${m.name}`} title="More" aria-haspopup="menu" aria-expanded={placement !== null} onClick={() => toggle()}>
        ⋯
      </button>
      {placement && (
        <Popover anchor={anchor} placement={placement} onClose={close} label={`More for ${m.name}`} role="menu" className="more-menu">
          <ul>{entries}</ul>
        </Popover>
      )}
    </>
  )
}

function Row({ m, a }: { m: Model; a: ModelActions }) {
  const mine = a.job?.model_id === m.id ? a.job : null
  const downloading = mine !== null && isActive(mine)
  const failed = Boolean(m.check && !m.check.ok)
  const used = m.installed && a.inUse(m)
  const level = speedLevel(m)
  const nameOf = (code: string) => a.names?.[code] ?? SPEECH_LANGUAGES[code] ?? code.toUpperCase()
  const note = coverageNote(m, a.codes, nameOf)
  const downloadError = !downloading && mine?.state !== 'error' ? m.downloadError : null
  return (
    <li className="model-row">
      <div className="mr-main">
        <div className="mr-text">
          <div className="mr-name">
            <span className="name" title={m.name}>{m.name.replace(/\s*\(.*\)\s*$/, '')}</span>
            {m.badge && <span className="mr-badge">{m.badge}</span>}
            {m.custom && <span className="mr-badge plain">Added by you</span>}
          </div>
          <div className="muted mr-desc">{m.description}</div>
          <div className="muted mr-meta">
            <span>{formatBytes(m.sizeBytes)}</span>
            <span>{languageCount(m, nameOf)}</span>
            {m.installed && m.check?.ok && <span className="mr-ok">Works here</span>}
            {note && <span className="mr-warn">{note}</span>}
          </div>
          {downloadError && <div className="error mr-error">The download failed: {downloadError} Press Download to try again.</div>}
        </div>
        <span className="mr-speed" role="img" aria-label={`Speed ${level} of 4`} title={m.check?.ok ? 'Speed, measured on this Mac' : 'Speed (press Test to measure it on this Mac)'}>
          {[1, 2, 3, 4].map((n) => (
            <i key={n} className={n <= level ? 'on' : ''} style={{ height: 4 + n * 3 }} />
          ))}
        </span>
        <span className="mr-actions">
          {!m.installed ? (
            <button className="secondary small" disabled={a.busy || downloading || Boolean(a.offline)} title={a.offline ? 'Needs the internet (Work offline is on)' : undefined} onClick={() => a.onDownload(m.id)}>
              Download
            </button>
          ) : used ? (
            <span className="mr-inuse">In use</span>
          ) : (
            a.onUse && (
              <button className="secondary small" disabled={a.busy || failed} title={failed ? 'It does not work here' : undefined} onClick={() => a.onUse?.(m)}>
                Use
              </button>
            )
          )}
          <Menu m={m} a={a} />
          {m.installed && (
            <button className="quiet small icon mr-bin" aria-label={`Delete ${m.name}`} title={`Delete (frees ${formatBytes(m.sizeBytes)})`} disabled={a.busy} onClick={() => a.onDelete(m)}>
              <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
                {BIN}
              </svg>
            </button>
          )}
        </span>
      </div>
      {m.installed && failed && <CheckResult model={m} />}
      {downloading && mine && (
        <TransferProgress
          job={mine}
          speed={a.speed}
          onCancel={() =>
            cancelJob(mine.id)
              .then(() => new Promise((resolve) => setTimeout(resolve, 250))) // the process is ended at once: look again right away
              .then(() => getJob(mine.id))
              .then(a.onJob, () => undefined)
          }
        />
      )}
      {mine?.state === 'error' && (
        <p className="error">
          {mine.error}{' '}
          <button className="secondary small" onClick={() => a.onDownload(m.id)}>
            Try again
          </button>{' '}
          <span className="muted">Files that finished downloading are kept; the one being fetched starts again.</span>
        </p>
      )}
      {mine?.state === 'cancelled' && <p className="muted">Cancelled. What was downloaded has been removed, so downloading again starts from the beginning.</p>}
    </li>
  )
}

// The models of one kind as rows in a settings card: name, what it is, size and languages, speed, and one action (Download, Use, or In use).
// Installed models come first.
export function ModelList({ models, a }: { models: Model[]; a: ModelActions }) {
  const sorted = [...models.filter((m) => m.installed), ...models.filter((m) => !m.installed)]
  return (
    <ul className="model-rows">
      {sorted.map((m) => (
        <Row key={m.id} m={m} a={a} />
      ))}
    </ul>
  )
}
