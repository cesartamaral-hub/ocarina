import type { ReactNode, RefObject } from 'react'
import type { Placement } from '../placement'
import { MoreMenu } from '../MoreMenu'
import { Popover } from '../Popover'
import { useAnchoredPopover } from '../useAnchoredPopover'
import { TypographyControls } from '../TypographyControls'
import { keyLabel, keyOf } from '../shortcutKeys'

// The line above the text: where you are, and the few things you do to the page.
export function ReaderToolbar({
  bookId,
  title,
  highlights,
  onToggleHighlights,
  vocabOpen,
  onToggleVocab,
  focus,
  onToggleFocus,
  onLeave,
  translation,
  translationOn,
  tpAnchor,
  tpPlacement,
  tpToggle,
  tpClose,
  onEdit,
  onHelp,
}: {
  bookId: number
  title: string
  highlights: boolean
  onToggleHighlights: () => void
  vocabOpen: boolean
  onToggleVocab: () => void
  focus: boolean
  onToggleFocus: () => void
  onLeave: () => void // the pointer left the toolbar (focus mode hides it again)
  translation: ReactNode // the content of the Translation popover
  translationOn: boolean // a translation is being shown
  tpAnchor: RefObject<HTMLButtonElement | null> // the Translation popover is opened here and by the T key (see Reader)
  tpPlacement: Placement | null
  tpToggle: () => void
  tpClose: () => void
  onEdit: () => void
  onHelp: () => void
}) {
  const { anchor, placement, toggle, close } = useAnchoredPopover(380, 'end')
  return (
    <div className="reader-toolbar" role="toolbar" aria-label="Page tools" onMouseLeave={onLeave}>
      <a className="button quiet back focus-hide" href="#/" title="Back to your books">
        ← Books
      </a>
      <span className="reader-title muted focus-hide" title={title}>
        {title}
      </span>
      <span className="spacer" />
      <button ref={tpAnchor} className="quiet" aria-pressed={translationOn} aria-expanded={tpPlacement !== null} aria-haspopup="dialog" onClick={() => tpToggle()} title="A translated version of the text">
        Translation
      </button>
      {tpPlacement && (
        <Popover anchor={tpAnchor} placement={tpPlacement} onClose={tpClose} label="Translation" className="tp-popover">
          {translation}
        </Popover>
      )}
      <button className="quiet focus-hide" aria-pressed={vocabOpen} onClick={onToggleVocab} title={`How well you know the words (${keyLabel(keyOf('toggleVocab'))})`}>
        Vocabulary
      </button>
      <button className="quiet" aria-pressed={highlights} onClick={onToggleHighlights} title={`Colour the words by how well you know them (${keyLabel(keyOf('highlights'))})`}>
        Highlights
      </button>
      <button ref={anchor} className="quiet aa-button" aria-expanded={placement !== null} aria-haspopup="dialog" onClick={() => toggle()} title="Text appearance">
        Aa
      </button>
      {placement && (
        <Popover anchor={anchor} placement={placement} onClose={close} label="Text appearance" className="aa-popover">
          <TypographyControls />
        </Popover>
      )}
      <button className="quiet focus-toggle" aria-pressed={focus} onClick={onToggleFocus} title={`${focus ? 'Leave' : 'Enter'} focus mode: only the text and the player (${keyLabel(keyOf('focus'))})`}>
        {focus ? 'Leave focus' : 'Focus'}
      </button>
      <MoreMenu
        title="More: audio, edit text, keyboard shortcuts"
        items={[
          { label: 'Audio…', href: `#/book/${bookId}/audio` },
          { label: 'Edit text', onChoose: onEdit },
          { label: 'Keyboard shortcuts', onChoose: onHelp },
        ]}
      />
    </div>
  )
}
