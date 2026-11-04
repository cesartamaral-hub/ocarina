import { keyLabel, keyOf } from '../shortcutKeys'
import type { TranslationMode } from './translationView'

const LINES = [2, 6, 10, 14]

// A tiny picture of each way to show the text.
function Icon({ mode }: { mode: TranslationMode }) {
  return (
    <svg width="22" height="16" viewBox="0 0 22 16" aria-hidden="true">
      {mode === 'original' && LINES.map((y, i) => <rect key={y} x="3" y={y - 1} width={i === 3 ? 10 : 16} height="2" rx="1" fill="currentColor" />)}
      {mode === 'both' && (
        <>
          {LINES.map((y, i) => (
            <rect key={y} x="1" y={y - 1} width={i === 3 ? 5 : 8} height="2" rx="1" fill="currentColor" />
          ))}
          <rect x="10.5" y="1" width="1" height="14" fill="currentColor" opacity="0.35" />
          {LINES.map((y, i) => (
            <rect key={y} x="13" y={y - 1} width={i === 3 ? 4 : 8} height="2" rx="1" fill="currentColor" opacity="0.7" />
          ))}
        </>
      )}
      {mode === 'translation' && LINES.map((y, i) => <rect key={y} x="3" y={y - 1} width={i === 3 ? 10 : 16} height="2" rx="1" fill="currentColor" opacity="0.7" strokeDasharray="0" />)}
      {mode === 'translation' && <path d="M17.5 9.5 l2 2 l-2 2" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />}
    </svg>
  )
}

// The way the text is shown now, centred above it: the original, the original beside its translation, or the translation alone.
// With no translation on the page the other two open the Translation menu, where it can be made.
export function TranslationModes({
  mode,
  hasTranslation,
  targetName,
  onMode,
  onMake,
}: {
  mode: TranslationMode
  hasTranslation: boolean
  targetName: string
  onMode: (mode: TranslationMode) => void
  onMake: () => void
}) {
  const options: { mode: TranslationMode; label: string }[] = [
    { mode: 'original', label: 'Original' },
    { mode: 'both', label: 'Side by side' },
    { mode: 'translation', label: `${targetName} only` },
  ]
  return (
    <div className="mode-bar" role="group" aria-label="How the text is shown">
      {options.map((o) => (
        <button
          key={o.mode}
          type="button"
          className={`quiet small icon mode-icon${mode === o.mode ? ' on' : ''}${o.mode !== 'original' && !hasTranslation ? ' empty' : ''}`}
          aria-pressed={mode === o.mode}
          aria-label={o.label}
          title={`${o.label}${o.mode !== 'original' && !hasTranslation ? ' (not translated yet)' : ''} (${keyLabel(keyOf('cycleTranslation'))})`}
          onClick={() => (o.mode === 'original' || hasTranslation ? onMode(o.mode) : onMake())}
        >
          <Icon mode={o.mode} />
        </button>
      ))}
    </div>
  )
}
