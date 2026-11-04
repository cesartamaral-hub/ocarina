import { useEffect, useRef, useState } from 'react'
import type { Book } from './api'
import { useEscape } from './escape'
import { barParts, difficulty, DIFFICULTY_LABEL, duration } from './bookStats'

function SpeakerIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
      <path d="M2 6h3l4-3v10L5 10H2z" fill="currentColor" />
      <path d="M11 5.5a3.5 3.5 0 0 1 0 5M12.8 3.5a6 6 0 0 1 0 9" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  )
}

// The "more" menu of a row: closes on Esc, on a click outside and after a choice.
function MoreMenu({ title, items }: { title: string; items: { label: string; onChoose: () => void; danger?: boolean }[] }) {
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
    <span className="more" ref={box}>
      <button className="secondary" aria-label={`More for ${title}`} aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen(!open)}>
        ⋯
      </button>
      {open && (
        <ul className="more-menu" role="menu">
          {items.map((i) => (
            <li key={i.label} role="none">
              <button
                role="menuitem"
                className={i.danger ? 'link-button danger-text' : 'link-button'}
                onClick={() => {
                  setOpen(false)
                  i.onChoose()
                }}
              >
                {i.label}
              </button>
            </li>
          ))}
        </ul>
      )}
    </span>
  )
}

const number = (n: number) => n.toLocaleString('en')

function Numbers({ book }: { book: Book }) {
  const s = book.stats
  if (!s) return <span className="muted book-numbers">{book.indexing ? 'Counting words…' : '—'}</span>
  const level = difficulty(s.knownPercent)
  const parts = barParts(s)
  return (
    <div className="book-numbers" title={`${number(s.words)} words, ${number(s.unique)} different · about ${duration(s.minutes)} to read`}>
      <div className="numbers-line">
        <strong>{Math.round(s.knownPercent)}% known</strong>
        <span className={`chip-level ${level}`}>{DIFFICULTY_LABEL[level]}</span>
      </div>
      <div className="numbers-line muted">
        {number(s.newUnique)} new words · {number(s.words)} words
      </div>
      <div
        className="statusbar"
        role="img"
        aria-label={`${Math.round(parts.known)}% known, ${Math.round(parts.learning)}% learning, ${Math.round(parts.new)}% new`}
      >
        <i className="k" style={{ width: `${parts.known}%` }} />
        <i className="l" style={{ width: `${parts.learning}%` }} />
        <i className="n" style={{ width: `${parts.new}%` }} />
      </div>
    </div>
  )
}

export function BookRow({
  book,
  onEdit,
  onArchive,
  onDelete,
}: {
  book: Book
  onEdit: () => void
  onArchive: () => void
  onDelete: () => void
}) {
  const audio = book.hasAudio ? (book.ocarinaAudio ? 'Has audio made by Ocarina' : 'Has your own audio') : ''
  return (
    <div className="book-row">
      <div className="book-title">
        <a href={`#/book/${book.id}`}>{book.title}</a>
        {book.hasAudio && (
          <span className="audio-icon" role="img" aria-label={audio} title={audio}>
            <SpeakerIcon />
          </span>
        )}
        <div className="muted">
          {book.pages > 1 ? `page ${book.currentPage} of ${book.pages}` : '1 page'}
          {book.tags.length > 0 && ` · ${book.tags.join(', ')}`}
        </div>
      </div>
      <Numbers book={book} />
      <span className="row-actions">
        <a className="button secondary small" href={`#/book/${book.id}/read/${book.currentPage}`}>
          {book.currentPage > 1 ? 'Continue' : 'Read'}
        </a>
        <MoreMenu
          title={book.title}
          items={[
            { label: 'Edit', onChoose: onEdit },
            { label: book.archived ? 'Unarchive' : 'Archive', onChoose: onArchive },
            { label: 'Delete…', onChoose: onDelete, danger: true },
          ]}
        />
      </span>
    </div>
  )
}
