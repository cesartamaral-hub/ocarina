import type { LanguageSupport } from './api'
import { FEATURES, featureTitle, levelLabel } from './languageSupport'

// What Ocarina can do for a language: one pill per feature, marked ready, not downloaded yet, online only or not available.
export function SupportPills({ support }: { support: LanguageSupport }) {
  return (
    <span className="support">
      <span className={`support-level ${support.level}`}>{levelLabel(support.level)}</span>
      <span className="support-pills">
        {FEATURES.map((f) => (
          <span key={f.key} className={`support-pill ${support[f.key]}`} title={featureTitle(f.label, f.what, support[f.key])}>
            {f.label}
            <span className="sr-only"> {support[f.key]}</span>
          </span>
        ))}
      </span>
    </span>
  )
}
