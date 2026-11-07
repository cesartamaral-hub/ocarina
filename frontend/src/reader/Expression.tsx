import { useEffect, useState } from 'react'
import { getParts, getTranslateSettings, glossSelection, type Gloss, type SelectionPart } from '../api'
import { useOffline } from '../offline'

// What a selection of several words can mean as a whole: the expressions and words the dictionaries on this Mac know inside it, and a
// machine's reading of the selection in its sentence (shown as that, never as a dictionary fact). With an online service the reading
// comes by itself; with the local model (a couple of seconds) it waits for a button. "Use" copies a meaning into the translation.
export function Expression({
  languageId,
  text,
  sentence,
  onUse,
}: {
  languageId: number
  text: string
  sentence?: string
  onUse: (meaning: string) => void
}) {
  const offline = useOffline()
  const [parts, setParts] = useState<{ text: string; found: SelectionPart[] }>({
    text: '',
    found: [],
  })
  const [gloss, setGloss] = useState<{
    text: string
    value: Gloss | null
    error: string
  }>({ text: '', value: null, error: '' })
  const [auto, setAuto] = useState<boolean | null>(null) // an online service answers by itself; the local model on request
  const [asked, setAsked] = useState('')

  useEffect(() => {
    getTranslateSettings().then(
      (s) => setAuto(s.provider !== 'local'),
      () => setAuto(false),
    )
  }, [])

  useEffect(() => {
    let current = true
    getParts(languageId, text).then(
      (r) => current && setParts({ text, found: r.parts }),
      () => current && setParts({ text, found: [] }),
    )
    return () => {
      current = false
    }
  }, [languageId, text])

  const wanted = auto === true && !offline ? text : asked
  useEffect(() => {
    if (wanted !== text) return
    let current = true
    glossSelection(languageId, text, sentence).then(
      (value) => current && setGloss({ text, value, error: '' }),
      (e) => current && setGloss({ text, value: null, error: e.message }),
    )
    return () => {
      current = false
    }
  }, [languageId, text, sentence, wanted])

  const shown = parts.text === text ? parts.found : []
  const g = gloss.text === text ? gloss : null
  return (
    <section className="expression" aria-label={`Meaning of the selection ${text}`}>
      {shown.length > 0 && (
        <div className="expr-parts">
          <div className="def-lemma-title">Inside this selection</div>
          {shown.map((p) => (
            <div key={p.text} className="expr-part">
              <strong>{p.text}</strong>
              {p.words > 1 && <span className="muted"> · expression</span>}
              {p.entries.slice(0, 2).map((e) => (
                <div key={e.partOfSpeech} className="expr-def">
                  <span className="muted">{e.partOfSpeech}</span>{' '}
                  {e.definitions.slice(0, 2).map((d, i) => (
                    <span key={i}>
                      {i > 0 && '; '}
                      {d.text}{' '}
                      <button
                        className="link-button"
                        onClick={() => onUse(d.text)}
                        aria-label={`Use “${d.text}” as the meaning`}
                      >
                        Use
                      </button>
                    </span>
                  ))}
                </div>
              ))}
              <span className="muted def-source">{p.source.name}</span>
            </div>
          ))}
        </div>
      )}
      <div className="expr-gloss">
        {g?.value ? (
          <p>
            <span className="muted">In this sentence, machine translation (check it): </span>
            <strong>{g.value.translation}</strong>{' '}
            <button className="link-button" onClick={() => onUse(g.value!.translation)}>
              Use
            </button>
            {!g.value.inContext && <span className="muted"> · the selection alone</span>}
          </p>
        ) : g?.error ? (
          <p className="muted">{g.error}</p>
        ) : wanted === text ? (
          <p className="muted">Reading “{text}” in its sentence…</p>
        ) : (
          <button
            className="secondary small"
            onClick={() => setAsked(text)}
            title="Ask the translation model what this means in the sentence"
          >
            What does this mean here?
          </button>
        )}
      </div>
    </section>
  )
}
