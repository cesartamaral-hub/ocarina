import { isActive } from '../api'
import { MODES, type TranslationMode } from './translationView'
import { TranslateSplit } from './TranslateSplit'
import type { useBookTranslation } from './useBookTranslation'

const n = (x: number) => x.toLocaleString('en')

// The Translation popover in the reader toolbar: how to show it, and making it.
export function TranslationPanel({
  tr,
  mode,
  onMode,
  page,
  pageHasTranslation,
}: {
  tr: ReturnType<typeof useBookTranslation>
  mode: TranslationMode
  onMode: (mode: TranslationMode) => void
  page: number
  pageHasTranslation: boolean
}) {
  const d = tr.data
  if (!d) return <p className="muted">Loading…</p>
  const label: Record<TranslationMode, string> = { original: 'Original', both: 'Side by side', translation: `${d.targetName} only` }
  const pageChars = d.remainingByPage[String(page)] ?? 0
  const over = d.dailyLimit !== null && d.remainingChars > d.dailyLimit * 0.8
  const running = tr.running
  return (
    <div className="translation-panel">
      <h3>Translation into {d.targetName}</h3>

      <div className="segmented" role="radiogroup" aria-label="How the text is shown">
        {MODES.map((m) => {
          const available = m === 'original' || pageHasTranslation
          return (
            <label key={m} className={`${mode === m ? 'on' : ''}${available ? '' : ' off'}`} title={available ? undefined : 'This page has no translation yet'}>
              <input type="radio" name="translation-mode" value={m} checked={mode === m} disabled={!available} onChange={() => onMode(m)} />
              {label[m]}
            </label>
          )
        })}
      </div>
      {!pageHasTranslation && <p className="muted tp-note">This page has no translation yet.</p>}

      <p className="tp-count">
        <strong>
          {n(d.done)} of {n(d.total)}
        </strong>{' '}
        sentences translated{d.stale > 0 && <span className="muted"> · {n(d.stale)} changed since</span>}
      </p>
      <progress value={d.done} max={Math.max(d.total, 1)} aria-label="Sentences translated" />

      {running && tr.job ? (
        <div className="tp-running">
          <span className="muted">
            {tr.job.state === 'queued' ? 'Waiting…' : `Translating · ${n(tr.job.done)} / ${tr.job.total || '…'}`}
          </span>
          <button className="secondary small" onClick={tr.cancel}>
            Cancel
          </button>
        </div>
      ) : (
        <div className="tp-actions">
          <TranslateSplit
            label="Translate this page"
            methods={d.methods}
            primary
            disabled={pageChars === 0}
            title={pageChars === 0 ? 'Every sentence of this page is translated' : undefined}
            onRun={(method) => tr.start('page', page, method)}
          />
          <TranslateSplit label="Translate the whole book" methods={d.methods} primary={false} disabled={d.remainingChars === 0} onRun={(method) => tr.start('book', undefined, method)} />
        </div>
      )}
      {tr.job?.state === 'error' && <p className="error tp-note">{tr.job.error}</p>}
      {tr.job?.state === 'cancelled' && <p className="muted tp-note">Cancelled. What was translated is kept.</p>}
      {tr.job?.state === 'done' && !isActive(tr.job) && tr.job.total === 0 && <p className="muted tp-note">Nothing was left to translate.</p>}
      {tr.error && <p className="error tp-note">{tr.error}</p>}

      <p className="muted tp-note">
        {d.done > 0 ? 'Made with' : 'Translates with'} <strong>{d.providerName}</strong> by default. <a href="#/settings/translation">Change</a>
      </p>
      {over && !running && (
        <p className="tp-warn">
          {d.providerName} allows about {n(d.dailyLimit!)} characters a day, and this book needs about {n(d.remainingChars)}. A model on this Mac, or DeepL, has no such limit.
        </p>
      )}

      {d.done > 0 && !running && (
        <button
          className="link-button danger-text"
          onClick={() => {
            if (window.confirm('Remove the translation of this whole book? You can make it again.')) tr.remove()
          }}
        >
          Remove the translation
        </button>
      )}
    </div>
  )
}
