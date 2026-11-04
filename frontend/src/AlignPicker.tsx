import { ALIGNMENTS, type Align } from './typography'

// Four small buttons showing how lines are laid out; one is on.
export function AlignPicker({ value, onChange }: { value: Align; onChange: (value: Align) => void }) {
  return (
    <div className="tc-align" role="radiogroup" aria-label="Alignment">
      {ALIGNMENTS.map((a) => (
        <button
          key={a.value}
          type="button"
          role="radio"
          aria-checked={value === a.value}
          aria-label={a.label}
          title={a.label}
          className={value === a.value ? 'on' : 'secondary'}
          onClick={() => onChange(a.value)}
        >
          <svg width="16" height="14" viewBox="0 0 16 14" aria-hidden="true">
            {[0, 4, 8, 12].map((y, i) => {
              const w = a.value === 'justify' || i % 2 === 0 ? 16 : 10
              const x = a.value === 'center' ? (16 - w) / 2 : a.value === 'end' ? 16 - w : 0
              return <rect key={y} x={x} y={y} width={w} height="2" rx="1" fill="currentColor" />
            })}
          </svg>
        </button>
      ))}
    </div>
  )
}
