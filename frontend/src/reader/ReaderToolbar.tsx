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
  onEdit,
  onHelp,
}: {
  bookId: number
  title: string
  highlights: boolean
  onToggleHighlights: () => void
  onEdit: () => void
  onHelp: () => void
}) {
  const { anchor, placement, toggle, close } = useAnchoredPopover(380, 'end')
  return (
    <div className="reader-toolbar" role="toolbar" aria-label="Page tools">
      <a className="button quiet back" href="#/" title="Back to your books">
        ← Books
      </a>
      <span className="reader-title muted" title={title}>
        {title}
      </span>
      <span className="spacer" />
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
