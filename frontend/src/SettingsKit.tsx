import type { ReactNode } from 'react'

// The building blocks of the settings pages: an uppercase label over a card of rows; each row has a label with an (i) tip on the left and its control on the right.

export function SettingsGroup({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="set-group">
      <h2 className="set-group-title">{title}</h2>
      <div className="set-card">{children}</div>
    </section>
  )
}

export function InfoTip({ text, label }: { text: string; label: string }) {
  return (
    <span className="info-tip">
      <button type="button" className="info-btn" aria-label={`About ${label}`}>
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" aria-hidden="true">
          <circle cx="8" cy="8" r="6.5" />
          <path d="M8 7.2v3.6" strokeLinecap="round" />
          <circle cx="8" cy="4.9" r="0.4" fill="currentColor" />
        </svg>
      </button>
      <span role="tooltip" className="info-bubble">
        {text}
      </span>
    </span>
  )
}

export function SettingRow({ label, info, hint, disabled, children }: { label: string; info?: string; hint?: string; disabled?: boolean; children?: ReactNode }) {
  return (
    <div className={`set-row${disabled ? ' disabled' : ''}`}>
      <div className="set-labelbox">
        <div className="set-label">
          <span>{label}</span>
          {info && <InfoTip text={info} label={label} />}
        </div>
        {hint && <span className="set-hint">{hint}</span>}
      </div>
      {children && <div className="set-control">{children}</div>}
    </div>
  )
}

export function Toggle({ checked, onChange, label, disabled }: { checked: boolean; onChange: (on: boolean) => void; label: string; disabled?: boolean }) {
  return (
    <button type="button" className="switch" role="switch" aria-checked={checked} aria-label={label} disabled={disabled} onClick={() => onChange(!checked)}>
      <span className="switch-knob" />
    </button>
  )
}
