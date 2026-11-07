import { NoLocalModelNotice } from '../NoLocalModelNotice'
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
  pageCount,
  pageHasTranslation,
}: {
  tr: ReturnType<typeof useBookTranslation>
  mode: TranslationMode
  onMode: (mode: TranslationMode) => void
  page: number
  pageCount: number
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
        sentences translated
        {d.stale > 0 && <span className="muted"> · {n(d.stale)} changed since</span>}
      </p>
      <progress value={d.done} max={Math.max(d.total, 1)} aria-label="Sentences translated" />

      {d.offline && !running && !d.methods.some((m) => m.available) ? (
        <p className="tp-warn">
          <NoLocalModelNotice />
        </p>
      ) : running && tr.job ? (
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
          {pageCount > 1 ? (
            <>
              <TranslateSplit
                label="Translate this page"
                methods={d.methods}
                primary
                disabled={pageChars === 0}
                title={pageChars === 0 ? 'Every sentence of this page is translated' : undefined}
                onRun={(method) => tr.start('page', page, method)}
              />
              <TranslateSplit label="Translate the whole material" methods={d.methods} primary={false} disabled={d.remainingChars === 0} onRun={(method) => tr.start('book', undefined, method)} />
            </>
          ) : (
            <TranslateSplit
              label="Translate this material"
              methods={d.methods}
              primary
              disabled={d.remainingChars === 0}
              title={d.remainingChars === 0 ? 'Every sentence is translated' : undefined}
              onRun={(method) => tr.start('book', undefined, method)}
            />
          )}
        </div>
      )}
      {!running && d.done > 0 && (
        <div className="tp-actions tp-again">
          <span className="muted">Translate again</span>
          {pageCount > 1 && (
            <TranslateSplit
              label="This page"
              methods={d.methods}
              primary={false}
              disabled={!pageHasTranslation}
              title={
                pageHasTranslation
                  ? "Replace this page's translation with a new one"
                  : 'This page has no translation yet'
              }
              onRun={(method) => {
                if (
                  window.confirm(
                    'Translate this page again? The new translation replaces the current one (sentences you worded yourself are kept).',
                  )
                )
                  tr.start('page', page, method, true)
              }}
            />
          )}
          <TranslateSplit
            label={pageCount > 1 ? 'The whole material' : 'This material'}
            methods={d.methods}
            primary={false}
            disabled={false}
            title="Replace every translation with a new one"
            onRun={(method) => {
              if (
                window.confirm(
                  `Translate ${pageCount > 1 ? `all ${pageCount} pages` : 'this material'} again? The new translation replaces the current one (sentences you worded yourself are kept). The old one stays until each sentence is done.`,
                )
              )
                tr.start('book', undefined, method, true)
            }}
          />
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
          {d.providerName} allows about {n(d.dailyLimit!)} characters a day, and this material needs about {n(d.remainingChars)}. A local model, or DeepL, has no such limit.
        </p>
      )}

      {d.done > 0 && !running && (
        <button
          className="link-button danger-text"
          onClick={() => {
            if (window.confirm('Remove the translation of this whole material? You can make it again.')) tr.remove()
          }}
        >
          Remove the translation
        </button>
      )}
    </div>
  )
}
