import { useEffect, useRef, useState } from 'react'
import { TypographyControls } from '../TypographyControls'
import { keyLabel, keyOf } from '../shortcutKeys'

// The line above the text: where you are, and the few things you do to the page.
export function ReaderToolbar({
  bookId,
  title,
  page,
  pageCount,
  highlights,
  onToggleHighlights,
  onEdit,
  onHelp,
}: {
  bookId: number
  title: string
  page: number
  pageCount: number
  highlights: boolean
  onToggleHighlights: () => void
  onEdit: () => void
  onHelp: () => void
}) {
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLSpanElement>(null)
  useEffect(() => {
    if (!open) return
    const away = (e: MouseEvent) => {
      if (!box.current?.contains(e.target as Node)) setOpen(false)
    }
    const esc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', away)
    document.addEventListener('keydown', esc)
    return () => {
      document.removeEventListener('mousedown', away)
      document.removeEventListener('keydown', esc)
    }
  }, [open])
  return (
    <p className="muted reader-toolbar">
      <a href={`#/book/${bookId}`}>← {title}</a> · page {page} of {pageCount} ·{' '}
      <a
        href="#edit"
        onClick={(e) => {
          e.preventDefault()
          onEdit()
        }}
      >
        Edit text
      </a>{' '}
      ·{' '}
      <label className="inline">
        <input type="checkbox" checked={highlights} onChange={onToggleHighlights} /> Highlights ({keyLabel(keyOf('highlights'))})
      </label>{' '}
      ·{' '}
      <span className="aa-box" ref={box}>
        <button type="button" className="secondary aa-button" aria-expanded={open} aria-haspopup="dialog" onClick={() => setOpen(!open)} title="Text appearance">
          Aa
        </button>
        {open && (
          <div className="aa-popover" role="dialog" aria-label="Text appearance">
            <TypographyControls />
          </div>
        )}
      </span>{' '}
      ·{' '}
      <a
        href="#keys"
        onClick={(e) => {
          e.preventDefault()
          onHelp()
        }}
      >
        Keys
      </a>
    </p>
  )
}
