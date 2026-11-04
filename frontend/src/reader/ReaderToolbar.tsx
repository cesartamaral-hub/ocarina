import { useEffect, useRef, useState } from 'react'
import { useEscape } from '../escape'
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
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLSpanElement>(null)
  useEscape(open, () => setOpen(false))
  useEffect(() => {
    if (!open) return
    const away = (e: MouseEvent) => {
      if (!box.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', away)
    return () => {
      document.removeEventListener('mousedown', away)
    }
  }, [open])
  return (
    <div className="reader-toolbar" role="toolbar" aria-label="Page tools">
      <a className="button quiet back" href={`#/book/${bookId}`} title={`Back to ${title}`}>
        ← {title}
      </a>
      <span className="spacer" />
      <button className="quiet" aria-pressed={highlights} onClick={onToggleHighlights} title={`Colour the words by how well you know them (${keyLabel(keyOf('highlights'))})`}>
        Highlights
      </button>
      <button className="quiet" onClick={onEdit}>
        Edit text
      </button>
      <span className="aa-box" ref={box}>
        <button className="quiet aa-button" aria-expanded={open} aria-haspopup="dialog" onClick={() => setOpen(!open)} title="Text appearance">
          Aa
        </button>
        {open && (
          <div className="aa-popover" role="dialog" aria-label="Text appearance">
            <TypographyControls />
          </div>
        )}
      </span>
      <button className="quiet" onClick={onHelp} title="Keyboard shortcuts">
        Keys
      </button>
    </div>
  )
}
