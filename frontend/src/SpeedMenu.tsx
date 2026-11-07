import { Popover } from './Popover'
import { SPEED_PRESETS, presetFor, speedLabel } from './speeds'
import { useAnchoredPopover } from './useAnchoredPopover'

// "⋯" next to the speed slider: the usual speeds in one click.
export function SpeedMenu({ speed, onChange, labelled = false }: { speed: number; onChange: (speed: number) => void; labelled?: boolean }) {
  const { anchor, placement, toggle, close } = useAnchoredPopover(130, 'end')
  const current = presetFor(speed)
  return (
    <>
      <button ref={anchor} type="button" className={labelled ? 'quiet small speed-chip' : 'secondary small icon'} aria-label="Speeds" title="Common speeds" aria-haspopup="menu" aria-expanded={placement !== null} onClick={() => toggle()}>
        {labelled ? speedLabel(speed) : '⋯'}
      </button>
      {placement && (
        <Popover anchor={anchor} placement={placement} onClose={close} label="Playback speed" role="menu" className="more-menu speed-menu">
          <ul>
            {SPEED_PRESETS.map((p) => (
              <li key={p} role="none">
                <button
                  role="menuitemradio"
                  aria-checked={current === p}
                  className="link-button"
                  onClick={() => {
                    close()
                    onChange(p)
                  }}
                >
                  <span className="menu-check" aria-hidden="true">
                    {current === p ? '✓' : ''}
                  </span>
                  {speedLabel(p)}
                </button>
              </li>
            ))}
          </ul>
        </Popover>
      )}
    </>
  )
}
