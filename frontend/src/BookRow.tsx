import type { Book } from './api'
import { MoreMenu } from './MoreMenu'
import { barParts, readingTime } from './bookStats'

function SpeakerIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
      <path d="M2 6h3l4-3v10L5 10H2z" fill="currentColor" />
      <path d="M11 5.5a3.5 3.5 0 0 1 0 5M12.8 3.5a6 6 0 0 1 0 9" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  )
}

const number = (n: number) => n.toLocaleString('en')

function Numbers({ book }: { book: Book }) {
  const s = book.stats
  if (!s) return <span className="muted book-numbers">{book.indexing ? 'Counting words…' : '—'}</span>
  const parts = barParts(s)
  return (
    <div className="book-numbers" title={`${number(s.words)} words, ${number(s.unique)} different · ${readingTime(s.minutes)} to read`}>
      <div className="numbers-line">
        <strong>{Math.round(s.knownPercent)}% known</strong>
        <span className="muted">· {readingTime(s.minutes)}</span>
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
        <a href={`#/book/${book.id}/read/${book.currentPage}`}>{book.title}</a>
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
          title={`More for ${book.title}`}
          items={[
            { label: 'Audio…', href: `#/book/${book.id}/audio` },
            { label: 'Edit', onChoose: onEdit },
            { label: book.archived ? 'Unarchive' : 'Archive', onChoose: onArchive },
            { label: 'Delete…', onChoose: onDelete, danger: true },
          ]}
        />
      </span>
    </div>
  )
}
