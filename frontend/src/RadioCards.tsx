import type { ReactNode } from 'react'

export type CardOption<T extends string> = { value: T; label: string; hint?: string; preview?: ReactNode }

// A row of cards where exactly one is chosen. Real radio buttons underneath, so the arrow keys, Tab and screen readers work as they should.
export function RadioCards<T extends string>({
  name,
  label,
  value,
  options,
  onChange,
  className = '',
}: {
  name: string
  label: string
  value: T | null
  options: CardOption<T>[]
  onChange: (value: T) => void
  className?: string
}) {
  return (
    <div role="radiogroup" aria-label={label} className={`radio-cards ${className}`}>
      {options.map((o) => (
        <label key={o.value} className="radio-card">
          <input type="radio" name={name} value={o.value} checked={value === o.value} onChange={() => onChange(o.value)} />
          {o.preview && <span className="rc-preview">{o.preview}</span>}
          <span className="rc-label">{o.label}</span>
          {o.hint && <span className="rc-hint">{o.hint}</span>}
        </label>
      ))}
    </div>
  )
}
