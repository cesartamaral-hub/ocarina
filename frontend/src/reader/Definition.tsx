import { useEffect, useState } from 'react'
import { getDefinition, openExternal, type Definition as DefinitionData, type DefinitionEntry } from '../api'

const renderEntries = (entries: DefinitionEntry[], onUse: (meaning: string) => void, limit = 6) =>
  entries.map((entry, i) => (
    <div key={i} className="def-entry">
      <div className="def-pos">{entry.partOfSpeech}</div>
      <ol>
        {entry.definitions.slice(0, limit).map((d, j) => (
          <li key={j}>
            <span>{d.text}</span>{' '}
            <button className="link-button use" title="Add this meaning to the translation" onClick={() => onUse(d.text)}>
              Use
            </button>
            {d.examples[0] && <div className="def-example">{d.examples[0]}</div>}
          </li>
        ))}
      </ol>
    </div>
  ))

type State = { text: string; data: DefinitionData | null; error: string; offline: boolean }

// What the word means, from Wiktionary (cached on this Mac). "Use" copies a meaning into the translation.
export function Definition({
  languageId,
  text,
  onUse,
  onError,
}: {
  languageId: number
  text: string
  onUse: (meaning: string) => void
  onError: (message: string) => void
}) {
  const [state, setState] = useState<State>({ text: '', data: null, error: '', offline: false })
  const [tries, setTries] = useState(0)

  useEffect(() => {
    const stale = new AbortController() // an answer for a word you already moved away from is ignored
    getDefinition(languageId, text).then(
      (data) => !stale.signal.aborted && setState({ text, data, error: '', offline: false }),
      (e) => !stale.signal.aborted && setState({ text, data: null, error: e.message, offline: e.code === 'offline' }),
    )
    return () => stale.abort()
  }, [languageId, text, tries])

  const loading = state.text !== text
  const { data } = state
  return (
    <section className="definition" aria-label={`Definition of ${text}`} aria-busy={loading}>
      {loading ? (
        <p className="muted">Looking up “{text}”…</p>
      ) : state.error ? (
        <p className="muted">
          {state.error}
          {state.offline && ' Words you looked up before still work offline.'}{' '}
          <button className="link-button" onClick={() => setTries((n) => n + 1)}>
            Try again
          </button>
        </p>
      ) : data && data.found && data.entries ? (
        <>
          {/* For an inflected word the base form's meaning comes first: that is what it means. */}
          {data.lemmas?.map((lemma) => (
            <div key={lemma.word} className="def-lemma">
              <div className="def-lemma-title">
                Base form: <strong>{lemma.word}</strong>
              </div>
              {renderEntries(lemma.entries, onUse, 3)}
            </div>
          ))}
          {data.lemmas && data.lemmas.length > 0 && <div className="def-lemma-title this-form">This form</div>}
          {renderEntries(data.entries, onUse)}
          <p className="muted def-source">
            Wiktionary{data.stale ? ' · saved copy' : ''} ·{' '}
            <a
              href={data.url}
              onClick={(e) => {
                e.preventDefault()
                if (data.url) openExternal(data.url).catch((err) => onError(err.message))
              }}
            >
              Full entry ↗
            </a>
          </p>
        </>
      ) : (
        <p className="muted">No entry for “{text}” in Wiktionary. Try a dictionary below, or look up the words one by one.</p>
      )}
    </section>
  )
}
