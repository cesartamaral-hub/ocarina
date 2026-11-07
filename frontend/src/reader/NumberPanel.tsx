import { useEffect, useState } from 'react'
import { getNumberWords, type NumberWords } from '../api'
import { SpeakButton } from './SpeakButton'
import { wordsOf } from './numberText'

const KIND = { number: 'Number', year: 'Year', ordinal: 'Ordinal' }

// A number written in digits: how it is said in the language, with a button to hear it, and each word of it to look up (that opens the
// word's panel, where it can be saved). Nothing is added to your vocabulary unless you do that.
export function NumberPanel({
  languageId,
  text,
  onLookUp,
}: {
  languageId: number
  text: string
  onLookUp: (word: string) => void
}) {
  const [found, setFound] = useState<{
    text: string
    value: NumberWords | null
  }>({ text: '', value: null })
  useEffect(() => {
    let current = true
    getNumberWords(languageId, text).then(
      (value) => current && setFound({ text, value }),
      () => current && setFound({ text, value: null }),
    )
    return () => {
      current = false
    }
  }, [languageId, text])

  const value = found.text === text ? found.value : null
  return (
    <section className="number-panel" aria-label={`The number ${text}`}>
      <h2>
        {text} <SpeakButton text={text} languageId={languageId} />
      </h2>
      {found.text !== text ? (
        <p className="muted">Looking up…</p>
      ) : value?.words ? (
        <>
          <p className="muted">{value.kind ? KIND[value.kind] : 'Number'}, written out:</p>
          <p className="number-words">{value.words}</p>
          <p className="muted">Look up a word:</p>
          <p className="number-chips">
            {wordsOf(value.words).map((w) => (
              <button key={w} className="secondary small" onClick={() => onLookUp(w)}>
                {w}
              </button>
            ))}
          </p>
        </>
      ) : (
        <p className="muted">Ocarina cannot write this number out in words.</p>
      )}
    </section>
  )
}
