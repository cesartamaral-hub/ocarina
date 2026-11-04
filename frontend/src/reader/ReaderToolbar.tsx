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
