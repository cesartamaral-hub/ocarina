import { useAnchoredPopover } from './useAnchoredPopover'
import { Popover } from './Popover'
import { formatBytes } from './format'
import { gradeLevel, speedLevel } from './modelRows'
import { TransferProgress } from './TransferProgress'
import { CheckResult } from './CheckResult'
import { cancelJob, isActive, type Job, type Model } from './api'

export type ModelActions = {
  busy: boolean
  job: Job | null
  speed: number
  codes: string[] // the languages shown as columns
  usedFor: (m: Model) => string[] | 'all' | null // where the model is used: all your languages, some of them, or nowhere
  onUse?: (m: Model) => void // makes it the model in use (when more than one can be)
  onDownload: (id: string) => void
  onImport: (m: Model) => void
  onTest: (m: Model) => void
  onDelete: (m: Model) => void
  onForget: (m: Model) => void
  onJob: (job: Job) => void
}

const CHECK = <path d="M4 8.5l2.7 2.7L12 5.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
const DOWNLOAD = <path d="M8 2.5v7.5M4.8 7.2L8 10.4l3.2-3.2M3 13h10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />

function Menu({ m, a }: { m: Model; a: ModelActions }) {
  const { anchor, placement, toggle, close } = useAnchoredPopover(220, 'end')
  const item = (label: string, run: () => void, danger = false) => (
    <li role="none">
      <button
        role="menuitem"
        className={danger ? 'danger-text' : undefined}
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
  return (
    <>
      <button ref={anchor} className="quiet small icon" aria-label={`More for ${m.name}`} title="More" aria-haspopup="menu" aria-expanded={placement !== null} onClick={() => toggle()}>
        ⋯
      </button>
      {placement && (
        <Popover anchor={anchor} placement={placement} onClose={close} label={`More for ${m.name}`} role="menu" className="more-menu">
          <ul>
            {m.installed && item(m.check ? 'Test again' : 'Test', () => a.onTest(m))}
            {!m.installed && item('Import from a folder…', () => a.onImport(m))}
            {m.custom && item('Remove from the list', () => a.onForget(m))}
            {m.installed && item(`Delete (${formatBytes(m.sizeBytes)})`, () => a.onDelete(m), true)}
          </ul>
        </Popover>
      )}
    </>
  )
}

function Row({ m, a }: { m: Model; a: ModelActions }) {
  const mine = a.job?.model_id === m.id ? a.job : null
  const downloading = mine !== null && isActive(mine)
  const used = m.installed ? a.usedFor(m) : null
  const failed = Boolean(m.check && !m.check.ok)
  const level = speedLevel(m)
  const partial = Array.isArray(used) && used.length > 0
  return (
    <li className={`model-row${used === 'all' ? ' in-use' : ''}`}>
      <div className="mr-main">
        <button
          className={`mr-mark${used === 'all' ? ' on' : ''}${partial ? ' some' : ''}`}
          aria-label={used === 'all' ? `${m.name} is in use` : m.installed ? `Use ${m.name}` : `Download ${m.name}`}
          aria-pressed={used === 'all'}
          title={used === 'all' ? 'In use' : m.installed ? (failed ? 'It does not work here' : 'Use this one') : `Download (${formatBytes(m.sizeBytes)})`}
          disabled={a.busy || downloading || (m.installed && (!a.onUse || failed || used === 'all'))}
          onClick={() => (m.installed ? a.onUse?.(m) : a.onDownload(m.id))}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
            {m.installed ? CHECK : DOWNLOAD}
          </svg>
        </button>
        <div className="mr-text">
          <div className="mr-name">
            <span className="name">{m.name}</span>
            {m.badge && <span className="mr-badge">{m.badge}</span>}
            {partial && <span className="muted mr-note">used for {(used as string[]).map((c) => c.toUpperCase()).join(', ')}</span>}
            {m.custom && <span className="mr-badge plain">added by you</span>}
          </div>
          <div className="muted mr-desc">{m.description}</div>
        </div>
        <div className="mr-grades">
          {a.codes.map((code) => {
            const grade = m.grades?.[code]
            const supported = m.languages.includes(code)
            return (
              <span key={code} data-code={code.toUpperCase()} className={`mr-grade ${gradeLevel(supported ? grade : undefined)}`} title={supported ? `${code.toUpperCase()}: ${grade ?? 'not rated'}` : `Does not support ${code.toUpperCase()}`}>
                {supported ? (grade ?? '—') : '·'}
              </span>
            )
          })}
        </div>
        <span className="mr-speed" role="img" aria-label={`Speed ${level} of 4`} title={m.check?.ok ? 'Measured on this Mac' : 'Speed (press Test to measure it on this Mac)'}>
          {[1, 2, 3, 4].map((n) => (
            <i key={n} className={n <= level ? 'on' : ''} style={{ height: 4 + n * 3 }} />
          ))}
        </span>
        <span className="muted mr-size">{formatBytes(m.sizeBytes)}</span>
        <span className="mr-actions">
          {m.installed && m.check?.ok && <span className="mr-ok" title="Works here" aria-label="Works here">✓</span>}
          <Menu m={m} a={a} />
        </span>
      </div>
      {m.installed && failed && <CheckResult model={m} />}
      {downloading && mine && <TransferProgress job={mine} speed={a.speed} onCancel={() => cancelJob(mine.id).then(a.onJob, () => undefined)} />}
      {mine?.state === 'error' && (
        <p className="error">
          {mine.error}{' '}
          <button className="secondary small" onClick={() => a.onDownload(m.id)}>
            Try again
          </button>{' '}
          <span className="muted">Files already downloaded are kept.</span>
        </p>
      )}
      {mine?.state === 'cancelled' && <p className="muted">Cancelled. Files already downloaded are kept, so downloading again continues from there.</p>}
    </li>
  )
}

// The models of one kind as compact rows: one in use is ticked, the languages you study have a grade each, then speed and size.
export function ModelList({ models, a }: { models: Model[]; a: ModelActions }) {
  const have = models.filter((m) => m.installed)
  const more = models.filter((m) => !m.installed)
  const head = (title: string) => (
    <div className="mr-head" aria-hidden="true">
      <span className="mr-head-title">{title}</span>
      <span className="mr-grades">
        {a.codes.map((c) => (
          <span key={c}>{c.toUpperCase()}</span>
        ))}
      </span>
      <span className="mr-speed-head">Speed</span>
      <span className="mr-size">Size</span>
      <span className="mr-actions" />
    </div>
  )
  return (
    <div className="model-list">
      {have.length > 0 && (
        <>
          {head('On this Mac')}
          <ul>
            {have.map((m) => (
              <Row key={m.id} m={m} a={a} />
            ))}
          </ul>
        </>
      )}
      {more.length > 0 && (
        <>
          {head(have.length > 0 ? 'To download' : 'Available')}
          <ul>
            {more.map((m) => (
              <Row key={m.id} m={m} a={a} />
            ))}
          </ul>
        </>
      )}
    </div>
  )
}
