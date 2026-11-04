import { useState } from 'react'
import type { BookStats } from '../api'
import { DIFFICULTY_LABEL, duration } from '../bookStats'
import { vocabularyBar, type NewWord, type PageVocabulary } from './vocabulary'

const SHOWN = 12
const n = (x: number) => x.toLocaleString('en')

function Bar({ parts }: { parts: { known: number; learning: number; fresh: number } }) {
  return (
    <div className="statusbar" role="img" aria-label={`${Math.round(parts.known)}% known, ${Math.round(parts.learning)}% learning, ${Math.round(parts.fresh)}% new`}>
      <i className="k" style={{ width: `${parts.known}%` }} />
      <i className="l" style={{ width: `${parts.learning}%` }} />
      <i className="n" style={{ width: `${parts.fresh}%` }} />
    </div>
  )
}

// How well you know the words of this page, updated as you set statuses, and of the book as a whole.
export function VocabularyPanel({
  vocab,
  page,
  pageCount,
  book,
  onPick,
  onClose,
}: {
  vocab: PageVocabulary
  page: number
  pageCount: number
  book: BookStats | null | undefined // undefined while loading, null while the book's words are being counted
  onPick: (word: NewWord) => void
  onClose: () => void
}) {
  const [all, setAll] = useState(false)
  const list = all ? vocab.newWords : vocab.newWords.slice(0, SHOWN)
  const bookBar = book ? { known: (100 * book.known) / Math.max(book.known + book.learning + book.new, 1), learning: (100 * book.learning) / Math.max(book.known + book.learning + book.new, 1), fresh: (100 * book.new) / Math.max(book.known + book.learning + book.new, 1) } : null
  return (
    <div className="vocab">
      <div className="vocab-head">
        <h2>Vocabulary</h2>
        <button className="secondary small icon vocab-close" onClick={onClose} aria-label="Close the vocabulary panel" title="Close (V)">
          ✕
        </button>
      </div>

      <section aria-labelledby="vocab-page">
        <h3 id="vocab-page">
          This page <span className="muted">{pageCount > 1 ? `${page} of ${pageCount}` : ''}</span>
        </h3>
        <p className="vocab-big">
          <strong>{Math.round(vocab.knownPercent)}%</strong> known <span className={`chip-level ${vocab.level}`}>{DIFFICULTY_LABEL[vocab.level]}</span>
        </p>
        <Bar parts={vocabularyBar(vocab)} />
        <dl className="vocab-rows">
          <div>
            <dt>
              <i className="dot k" /> Known
            </dt>
            <dd>
              {n(vocab.known.running)} <span className="muted">· {n(vocab.known.unique)} different</span>
            </dd>
          </div>
          <div>
            <dt>
              <i className="dot l" /> Learning
            </dt>
            <dd>
              {n(vocab.learning.running)} <span className="muted">· {n(vocab.learning.unique)} different</span>
            </dd>
          </div>
          <div>
            <dt>
              <i className="dot n" /> New
            </dt>
            <dd>
              {n(vocab.fresh.running)} <span className="muted">· {n(vocab.fresh.unique)} different</span>
            </dd>
          </div>
          {vocab.ignored.running > 0 && (
            <div>
              <dt>Ignored</dt>
              <dd>{n(vocab.ignored.running)}</dd>
            </div>
          )}
        </dl>
        {vocab.learning.unique > 0 && (
          <p className="muted vocab-stages">
            Learning stages: {([1, 2, 3] as const).map((s) => `${s}: ${vocab.learning.byStatus[s]}`).join(' · ')}
          </p>
        )}
        <p className="muted vocab-small">
          {n(vocab.words)} words · {n(vocab.unique)} different · {duration(vocab.minutes)} to read
        </p>
      </section>

      <section aria-labelledby="vocab-new">
        <h3 id="vocab-new">
          New on this page <span className="muted">{vocab.newWords.length}</span>
        </h3>
        {vocab.newWords.length === 0 ? (
          <p className="muted">Every word on this page is one you have started on.</p>
        ) : (
          <>
            <ul className="vocab-new">
              {list.map((w) => (
                <li key={w.text.toLowerCase()}>
                  <button className="link-button" onClick={() => onPick(w)} title="Show this word">
                    {w.text}
                  </button>
                  {w.count > 1 && <span className="muted">×{w.count}</span>}
                </li>
              ))}
            </ul>
            {vocab.newWords.length > SHOWN && (
              <button className="link-button" onClick={() => setAll(!all)}>
                {all ? 'Show fewer' : `Show all ${vocab.newWords.length}`}
              </button>
            )}
          </>
        )}
      </section>

      <section aria-labelledby="vocab-book">
        <h3 id="vocab-book">This book</h3>
        {book === undefined ? (
          <p className="muted">Loading…</p>
        ) : book === null ? (
          <p className="muted">Counting the words of the book…</p>
        ) : (
          <>
            <p className="vocab-big">
              <strong>{Math.round(book.knownPercent)}%</strong> known
            </p>
            {bookBar && <Bar parts={bookBar} />}
            <p className="muted vocab-small">
              {n(book.newUnique)} new words in all · {n(book.words)} words · about {duration(book.minutes)} to read
            </p>
            {pageCount > 1 && (
              <>
                <progress value={page - 1} max={pageCount} aria-label="Pages read" />
                <p className="muted vocab-small">
                  Page {page} of {pageCount}
                </p>
              </>
            )}
          </>
        )}
      </section>
    </div>
  )
}
