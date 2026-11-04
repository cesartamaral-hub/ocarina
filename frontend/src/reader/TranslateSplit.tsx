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
  return (
    <span className="split translate-split">
      <button className={primary ? undefined : 'secondary'} disabled={disabled} title={title} onClick={() => onRun()}>
        {label}
      </button>
      <button
        ref={anchor}
        className={`${primary ? '' : 'secondary '}icon-button`}
        disabled={disabled}
        aria-label={`${label} another way`}
        title="Another way, for this one time"
        aria-haspopup="menu"
        aria-expanded={placement !== null}
        onClick={() => toggle()}
      >
        ▾
      </button>
      {placement && (
        <Popover anchor={anchor} placement={placement} onClose={close} label="Another way to translate" role="menu" className="more-menu method-menu">
          <p className="muted method-head">Translate this one time with</p>
          <ul>
            {methods.map((m) => (
              <li key={`${m.provider}:${m.model}`} role="none">
                <button
                  role="menuitem"
                  className="link-button"
                  disabled={!m.available}
                  onClick={() => {
                    close()
                    onRun({ provider: m.provider, model: m.model })
                  }}
                >
                  <span>
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
