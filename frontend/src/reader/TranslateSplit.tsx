import { useState } from 'react'
import { Popover } from '../Popover'
import { useAnchoredPopover } from '../useAnchoredPopover'
import type { TranslationMethod } from '../api'

// A button that translates with the default method, and an arrow that lists the other ways for this one time.
export function TranslateSplit({
  label,
  methods,
  primary,
  disabled,
  title,
  onRun,
}: {
  label: string
  methods: TranslationMethod[]
  primary: boolean
  disabled: boolean
  title?: string
  onRun: (method?: { provider: string; model: string | null }) => void
}) {
  const { anchor, placement, toggle, close } = useAnchoredPopover(310, 'end')
  const [chosen, setChosen] = useState<string | null>(null)
  const picked = methods.find((m) => `${m.provider}:${m.model}` === chosen && m.available)
  return (
    <span className="split translate-split">
      <button className={primary ? undefined : 'secondary'} disabled={disabled} title={title} onClick={() => onRun(picked && { provider: picked.provider, model: picked.model })}>
        {label}
        {picked && <small className="method-picked"> · {picked.name}</small>}
      </button>
      <button
        ref={anchor}
        className={`${primary ? '' : 'secondary '}icon-button`}
        disabled={disabled}
        aria-label={`${label} another way`}
        title="Choose another way to translate"
        aria-haspopup="menu"
        aria-expanded={placement !== null}
        onClick={() => toggle()}
      >
        ▾
      </button>
      {placement && (
        <Popover anchor={anchor} placement={placement} onClose={close} label="Another way to translate" role="menu" className="more-menu method-menu">
          <p className="muted method-head">Choose how to translate</p>
          <ul>
            {methods.map((m) => (
              <li key={`${m.provider}:${m.model}`} role="none">
                <button
                  role="menuitemradio"
                  aria-checked={(picked ? picked === m : m.isDefault) || false}
                  className="link-button"
                  disabled={!m.available}
                  onClick={() => {
                    setChosen(`${m.provider}:${m.model}`)
                    close()
                  }}
                >
                  <span>
                    {(picked ? picked === m : m.isDefault) ? '✓ ' : ''}
                    {m.name}
                    {m.isDefault && <span className="muted"> · default</span>}
                  </span>
                  {m.reason && <small className="muted">{m.reason}</small>}
                </button>
              </li>
            ))}
          </ul>
        </Popover>
      )}
    </span>
  )
}
