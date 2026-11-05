import { useState } from 'react'
import type { BookStats } from '../api'
import { DIFFICULTY_LABEL, difficulty, duration } from '../bookStats'
import type { NewWord, PageVocabulary } from './vocabulary'

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

// How well you know the words of the material, as a whole, updated as you set statuses; and the new words of this page.
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
  book: BookStats | null | undefined // undefined while loading, null while the material's words are being counted
  onPick: (word: NewWord) => void
  onClose: () => void
}) {
  const [all, setAll] = useState(false)
  const list = all ? vocab.newWords : vocab.newWords.slice(0, SHOWN)
  // The numbers of the whole material; until they are counted, those of this page.
  const stats = book ?? {
    words: vocab.words,
    known: vocab.known.running,
    learning: vocab.learning.running,
    new: vocab.fresh.running,
    newUnique: vocab.fresh.unique,
    knownPercent: vocab.knownPercent,
    minutes: vocab.minutes,
  }
  const counted = Math.max(stats.known + stats.learning + stats.new, 1)
  const parts = { known: (100 * stats.known) / counted, learning: (100 * stats.learning) / counted, fresh: (100 * stats.new) / counted }
  const level = difficulty(stats.knownPercent)
  return (
    <div className="vocab">
      <div className="vocab-head">
        <h2>Vocabulary</h2>
        <button className="secondary small icon vocab-close" onClick={onClose} aria-label="Close the vocabulary panel" title="Close (V)">
          ✕
        </button>
      </div>
      <p className="vocab-size">
        {n(stats.words)} words · about {duration(stats.minutes)} to read
        {book === undefined || book === null ? <span className="muted"> · counting…</span> : null}
      </p>

      <section aria-labelledby="vocab-stats">
        <h3 id="vocab-stats">How well you know it</h3>
        <p className="vocab-big">
          <strong>{Math.round(stats.knownPercent)}%</strong> known <span className={`chip-level ${level}`}>{DIFFICULTY_LABEL[level]}</span>
        </p>
        <Bar parts={parts} />
        <dl className="vocab-rows">
          <div>
            <dt>
              <i className="dot k" /> Known
            </dt>
            <dd>{n(stats.known)}</dd>
          </div>
          <div>
            <dt>
              <i className="dot l" /> Learning
            </dt>
            <dd>{n(stats.learning)}</dd>
          </div>
          <div>
            <dt>
              <i className="dot n" /> New
            </dt>
            <dd>
              {n(stats.new)} <span className="muted">· {n(stats.newUnique)} different</span>
            </dd>
          </div>
        </dl>
        {pageCount > 1 && (
          <div className="vocab-progress">
            <progress value={page - 1} max={pageCount} aria-label="Pages read" />
            <p className="muted vocab-small">
              Page {page} of {pageCount}
            </p>
          </div>
        )}
      </section>

      <section aria-labelledby="vocab-new">
        <h3 id="vocab-new">
          {pageCount > 1 ? 'New words on this page' : 'New words'} <span className="muted">{vocab.newWords.length}</span>
        </h3>
        {vocab.newWords.length === 0 ? (
          <p className="muted">{pageCount > 1 ? 'Every word on this page is one you have started on.' : 'Every word here is one you have started on.'}</p>
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
    </div>
  )
}
