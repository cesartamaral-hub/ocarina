import { useEffect, useState } from 'react'
import { addPredefinedLanguages, getLanguageSupport, getLanguageTemplate, type LanguageSupport } from './api'
import { LanguagePicker } from './LanguagePicker'

// Pick languages (A to Z with a search on the left, your picks on the right) and add them, with the default dictionary and, if you want, the
// sample story of each. Used by Welcome and by Settings -> Languages -> Add languages; languages already in the library are not offered.
export function AddLanguages({ onAdded }: { onAdded: (names: string[], support: Record<string, LanguageSupport>) => void }) {
  const [available, setAvailable] = useState<string[]>([])
  const [withStory, setWithStory] = useState<string[]>([])
  const [chosen, setChosen] = useState<string[]>([])
  const [support, setSupport] = useState<Record<string, LanguageSupport>>({})
  const [withBooks, setWithBooks] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    getLanguageTemplate().then(
      (t) => {
        setAvailable(t.predefined)
        setWithStory(t.withStory ?? t.predefined)
        getLanguageSupport(t.predefined).then((rows) => setSupport(Object.fromEntries(rows.map((r) => [r.language, r]))), () => undefined)
      },
      (e) => setError(e.message),
    )
  }, [])

  async function add() {
    setError('')
    setBusy(true)
    try {
      await addPredefinedLanguages(chosen, withBooks)
      onAdded(chosen, support)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const stories = chosen.filter((n) => withStory.includes(n)).length
  return (
    <>
      <LanguagePicker available={available} chosen={chosen} support={support} onChange={setChosen} />
      {chosen.length === 0 || stories > 0 ? (
        <label className="inline">
          <input type="checkbox" checked={withBooks} onChange={(e) => setWithBooks(e.target.checked)} /> Also add the sample {chosen.length > 1 ? 'stories' : 'story'}
        </label>
      ) : (
        <p className="muted">There is no sample story for {chosen.length === 1 ? 'this language' : 'these languages'}.</p>
      )}
      {error && <p className="error">{error}</p>}
      <p>
        <button disabled={busy || chosen.length === 0} onClick={add}>
          {chosen.length === 0 ? 'Choose a language' : `Add ${chosen.length} ${chosen.length === 1 ? 'language' : 'languages'}`}
        </button>
      </p>
    </>
  )
}
