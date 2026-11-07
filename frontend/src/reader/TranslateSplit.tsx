import { useState } from 'react'
import { Popover } from '../Popover'
import { useAnchoredPopover } from '../useAnchoredPopover'
import type { TranslationMethod } from '../api'
import { formatEstimate, translationSeconds } from '../estimate'

// A button that translates with the default method, and an arrow that lists the other ways for this one time.
export function TranslateSplit({
  label,
  methods,
  primary,
  disabled,
  title,
  sentences,
  onRun,
}: {
  label: string
  methods: TranslationMethod[]
  primary: boolean
  disabled: boolean
  title?: string
  sentences?: number // how many it would translate, for the time shown
  onRun: (method?: { provider: string; model: string | null }) => void
}) {
  const { anchor, placement, toggle, close } = useAnchoredPopover(310, 'end')
  const [chosen, setChosen] = useState<string | null>(null)
  const picked = methods.find((m) => `${m.provider}:${m.model}` === chosen && m.available)
  const time = sentences ? formatEstimate(translationSeconds(sentences, picked ?? methods.find((m) => m.isDefault))) : ''
  return (
    <span className="split translate-split">
      <button className={primary ? undefined : 'secondary'} disabled={disabled} title={picked ? `${label} with ${picked.name}` : title} onClick={() => onRun(picked && { provider: picked.provider, model: picked.model })}>
        {label}
        {time && !disabled && <small className="method-picked"> · {time}</small>}
        {picked && <small className="method-picked"> · {picked.name.replace(/\s*\(.*\)\s*$/, '')}</small>}
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
