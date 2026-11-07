import { useEffect, useState } from 'react'
import { useOffline } from '../offline'
import { AUTO_WIKTIONARY, shouldLookUpOnline } from './autoLookup'
import {
  getDefinition,
  getPref,
  openExternal,
  type Definition as DefinitionData,
  type DefinitionEntry,
  type DictionarySource,
} from '../api'

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

type State = { text: string; data: DefinitionData | null; error: string; offline: boolean; asked: string } // asked: the word Wiktionary was asked about with this answer

const sourceLine = (source: DictionarySource | undefined) =>
  source ? `${source.name}${source.license ? ` · ${source.license}` : ''}${source.offline ? ' · local' : ''}` : 'Wiktionary'

// What the word means, from the dictionaries on this Mac (Settings → Dictionaries), and Wiktionary when none has it. "Use" copies a meaning into the translation.
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
  const [state, setState] = useState<State>({ text: '', data: null, error: '', offline: false, asked: '' })
  const [tries, setTries] = useState(0)
  const offline = useOffline()
  const [online, setOnline] = useState('') // the word for which Wiktionary was also asked

  useEffect(() => {
    const stale = new AbortController() // an answer for a word you already moved away from is ignored
    getDefinition(languageId, text, false, online === text).then(
      (data) => !stale.signal.aborted && setState({ text, data, error: '', offline: false, asked: online }),
      (e) =>
        !stale.signal.aborted &&
        setState({ text, data: null, error: e.message, offline: e.code === 'offline', asked: online }),
    )
    return () => stale.abort()
  }, [languageId, text, tries, online])

  const loading = state.text !== text
  const { data } = state

  // Wiktionary is asked by itself once a dictionary on this Mac has answered (after a moment, so moving across words sends nothing).
  const auto = shouldLookUpOnline({ offline, enabled: getPref(AUTO_WIKTIONARY, true), text })
  const askable =
    !loading &&
    !!data?.found &&
    !!data.source?.offline &&
    !data.others?.some((o) => o.source.id === 'wiktionary') &&
    online !== text
  useEffect(() => {
    if (!auto || !askable) return
    const timer = setTimeout(() => setOnline(text), 400)
    return () => clearTimeout(timer)
  }, [auto, askable, text])
  const asking = online === text && state.asked !== text && !!data?.found
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
            {sourceLine(data.source)}
            {data.stale ? ' · saved copy' : ''}
            {data.url && (
              <>
                {' · '}
                <a
                  href={data.url}
                  onClick={(e) => {
                    e.preventDefault()
                    if (data.url) openExternal(data.url).catch((err) => onError(err.message))
                  }}
                >
                  Full entry ↗
                </a>
              </>
            )}
          </p>
          {data.others?.map((other) => (
            <details key={other.source.id} className="def-other">
              <summary>Also in {other.source.name}</summary>
              {other.lemmas.map((lemma) => (
                <div key={lemma.word} className="def-lemma">
                  <div className="def-lemma-title">
                    Base form: <strong>{lemma.word}</strong>
                  </div>
                  {renderEntries(lemma.entries, onUse, 3)}
                </div>
              ))}
              {renderEntries(other.entries, onUse, 4)}
              <p className="muted def-source">{sourceLine(other.source)}</p>
            </details>
          ))}
          {asking && <p className="muted def-asking">Looking up on Wiktionary…</p>}
          {!offline &&
            !asking &&
            data.source?.offline &&
            !data.others?.some((o) => o.source.id === 'wiktionary') &&
            online !== text && (
              <button className="link-button def-online" onClick={() => setOnline(text)}>
                Also look it up on Wiktionary
              </button>
            )}
        </>
      ) : (
        <p className="muted">{offline ? `No entry for “${text}” in the local dictionaries. You can add more under Settings → Dictionaries, or turn Work offline off to ask Wiktionary.` : `No entry for “${text}” in your dictionaries or Wiktionary. Try a dictionary below, or look up the words one by one.`}</p>
      )}
    </section>
  )
}
