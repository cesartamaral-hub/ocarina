import type { Model } from './api'

// What trying an installed model showed: it works (and how fast), it does not (and why), or it was never tried.
export function CheckResult({ model }: { model: Model }) {
  const c = model.check
  if (!c) return model.custom ? <div className="muted">Not tested yet.</div> : null
  if (c.ok) {
    return (
      <div className="check-ok">
        ✓ Works here
        {c.secondsPerSecondOfAudio != null && <span className="muted"> · about {c.secondsPerSecondOfAudio} s per second of audio</span>}
        {c.secondsPerSentence != null && <span className="muted"> · about {c.secondsPerSentence} s per sentence</span>}
        {c.loadSeconds ? <span className="muted"> · loads in {c.loadSeconds} s</span> : null}
      </div>
    )
  }
  return (
    <div className="check-failed" role="alert">
      <strong>Doesn’t work here.</strong> {c.error}
      {c.detail && c.detail !== c.error && (
        <details>
          <summary>Technical details</summary>
          <code>{c.detail}</code>
        </details>
      )}
    </div>
  )
}
