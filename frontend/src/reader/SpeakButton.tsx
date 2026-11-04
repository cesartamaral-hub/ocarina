import { PRONOUNCE_SOURCES, type PronounceSource } from '../api'
import { Popover } from '../Popover'
import { defaultSource, say, stopSaying, useSaying } from '../pronouncer'
import { keyLabel, keyOf } from '../shortcutKeys'
import { useAnchoredPopover } from '../useAnchoredPopover'

const SPEAKER = (
  <>
    <path d="M2.5 6.2h2.3L8 3.5v9L4.8 9.8H2.5z" fill="currentColor" />
    <path d="M10.3 5.6a3.2 3.2 0 0 1 0 4.8M12 3.9a5.6 5.6 0 0 1 0 8.2" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
  </>
)
const STOP = <rect x="4" y="4" width="8" height="8" rx="1.2" fill="currentColor" />

// Hear a word or some words: the speaker button says it with the chosen source, the arrow picks another source for this one time.
export function SpeakButton({ text, languageId }: { text: string; languageId: number }) {
  const saying = useSaying()
  const { anchor, placement, toggle, close } = useAnchoredPopover(320, 'end')
  const here = saying?.text === text.replace(/\s+/g, ' ').trim()
  const words = text.trim().split(/\s+/).length
  const label = here ? 'Stop' : `Hear it (${keyLabel(keyOf('speak'))})`
  return (
    <span className="speak">
      <button type="button" className="quiet small icon" aria-label={label} title={label} aria-busy={here && saying?.state === 'loading'} onClick={() => say(text, languageId)}>
        <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
          {here ? STOP : SPEAKER}
        </svg>
      </button>
      <button ref={anchor} type="button" className="quiet small speak-more" aria-label="Hear it another way" title="Hear it another way" aria-haspopup="menu" aria-expanded={placement !== null} onClick={() => toggle()}>
        ▾
      </button>
      {placement && (
        <Popover anchor={anchor} placement={placement} onClose={close} label="Hear it another way" role="menu" className="more-menu method-menu">
          <p className="muted method-head">Hear it, this one time, with</p>
          <ul>
            {PRONOUNCE_SOURCES.map((s: { id: PronounceSource; name: string; detail: string }) => {
              const unusable = s.id === 'speaker' && words > 1
              return (
                <li key={s.id} role="none">
                  <button
                    role="menuitem"
                    className="link-button"
                    disabled={unusable}
                    onClick={() => {
                      close()
                      stopSaying()
                      say(text, languageId, s.id)
                    }}
                  >
                    <span>
                      {s.name}
                      {s.id === defaultSource() && <span className="muted"> · default</span>}
                    </span>
                    <small className="muted">{unusable ? 'Single words only' : s.detail}</small>
                  </button>
                </li>
              )
            })}
          </ul>
        </Popover>
      )}
    </span>
  )
}
