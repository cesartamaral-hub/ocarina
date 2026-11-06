import { useEffect, useRef, useState } from 'react'
import { choosePortuguese, getLegacyPortuguese } from './api'
import { useEscape } from './escape'
import { notify } from './notices'

// A library from before Portuguese came in two kinds has a language called just "Portuguese". Once, at start, this asks which one it is and renames
// it (books, terms and settings stay as they are). Closing the question with Esc means Brazilian Portuguese.
export function LegacyPortuguese() {
  const [language, setLanguage] = useState<{ id: number } | null>(null)
  const dialog = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    getLegacyPortuguese().then(setLanguage, () => undefined)
  }, [])
  useEffect(() => {
    const el = dialog.current
    if (language && el && !el.open) el.showModal()
  }, [language])

  async function choose(kind: 'european' | 'brazilian') {
    if (!language) return
    try {
      const done = await choosePortuguese(language.id, kind)
      notify(`Your Portuguese is now ${done.name}`)
    } catch (e) {
      notify((e as Error).message, 6000)
    }
    setLanguage(null)
  }
  useEscape(language !== null, () => choose('brazilian'))

  if (!language) return null
  return (
    <dialog ref={dialog} className="update-dialog" aria-labelledby="pt-title" onCancel={(e) => e.preventDefault()}>
      <header className="ud-head">
        <h2 id="pt-title">Which Portuguese do you study?</h2>
        <p className="muted">Ocarina now tells them apart: voices, dictionaries and translation follow the one you pick. Your books and words stay as they are. Brazilian Portuguese is used if you skip this.</p>
      </header>
      <footer className="ud-foot">
        <button className="secondary" onClick={() => choose('european')}>
          European Portuguese
        </button>
        <button onClick={() => choose('brazilian')}>Brazilian Portuguese</button>
      </footer>
    </dialog>
  )
}
