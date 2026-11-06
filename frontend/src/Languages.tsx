import { useEffect, useState } from 'react'
import {
  deleteLanguage,
  getLanguageSettings,
  getLanguageTemplate,
  getLanguageSupport,
  getLanguages,
  getParsers,
  saveLanguage,
  type DictionarySetting,
  type Language,
  type LanguageSupport,
  type LanguageSettings,
} from './api'
import { SupportPills } from './SupportPills'

export function LanguageList() {
  const [languages, setLanguages] = useState<Language[] | null>(null)
  const [support, setSupport] = useState<Record<string, LanguageSupport>>({})
  const [error, setError] = useState('')
  useEffect(() => {
    getLanguages().then(setLanguages, (e) => setError(e.message))
    getLanguageSupport().then((rows) => setSupport(Object.fromEntries(rows.map((r) => [r.language, r]))), () => undefined)
  }, [])
  if (error) return <p className="error">{error}</p>
  if (!languages) return <p className="muted">Loading…</p>
  return (
    <>
      <div className="title-row">
        <h1>Languages</h1>
        <a href="#/settings/languages/new" className="button">
          Add a language
        </a>
      </div>
      <ul className="books">
        {languages.map((l) => (
          <li key={l.id}>
            <a href={`#/settings/languages/${l.id}`}>{l.name}</a>
            <span className="muted">
              {l.books} {l.books === 1 ? 'book' : 'books'} · {l.terms} terms
            </span>
            {support[l.name] && <SupportPills support={support[l.name]} />}
          </li>
        ))}
      </ul>
    </>
  )
}

const BLANK_DICTIONARY: DictionarySetting = { useFor: 'terms', dictType: 'embeddedhtml', url: '', active: true }

export function LanguageEditor({ languageId }: { languageId: number | null }) {
  const [lang, setLang] = useState<LanguageSettings | null>(null)
  const [parsers, setParsers] = useState<{ type: string; name: string }[]>([])
  const [predefined, setPredefined] = useState<string[]>([])
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    getParsers().then(setParsers, () => undefined)
    if (languageId === null) {
      getLanguageTemplate().then(
        (t) => {
          setLang(t.language)
          setPredefined(t.predefined)
        },
        (e) => setError(e.message),
      )
    } else {
      getLanguageSettings(languageId).then(setLang, (e) => setError(e.message))
    }
  }, [languageId])

  if (!lang) return error ? <p className="error">{error}</p> : <p className="muted">Loading…</p>

  const set = (patch: Partial<LanguageSettings>) => {
    setSaved(false)
    setLang({ ...lang, ...patch })
  }
  const setDict = (i: number, patch: Partial<DictionarySetting>) =>
    set({ dictionaries: lang.dictionaries.map((d, j) => (j === i ? { ...d, ...patch } : d)) })
  const move = (i: number, by: number) => {
    const list = [...lang.dictionaries]
    const [item] = list.splice(i, 1)
    list.splice(i + by, 0, item)
    set({ dictionaries: list })
  }

  async function startFrom(name: string) {
    try {
      const t = await getLanguageTemplate(name || undefined)
      setLang(t.language)
    } catch (e) {
      setError((e as Error).message)
    }
  }

  async function save() {
    setError('')
    try {
      const result = await saveLanguage(lang!)
      if (languageId === null) window.location.hash = `#/settings/languages/${result.id}`
      else {
        setLang(result)
        setSaved(true)
      }
    } catch (e) {
      setError((e as Error).message)
    }
  }

  async function remove() {
    if (languageId === null) return
    setError('')
    try {
      await deleteLanguage(languageId, false)
      window.location.hash = '#/settings/languages'
    } catch (e) {
      const err = e as Error & { books?: number; terms?: number }
      if (err.books === undefined) return setError(err.message)
      const typed = window.prompt(
        `Deleting ${lang!.name} also deletes its ${err.books} books and ${err.terms} terms. This cannot be undone.\nType the language name to confirm.`,
      )
      if (typed?.trim() !== lang!.name) return
      try {
        await deleteLanguage(languageId, true)
        window.location.hash = '#/settings/languages'
      } catch (e2) {
        setError((e2 as Error).message)
      }
    }
  }

  return (
    <>
      <p>
        <a href="#/settings/languages">← Languages</a>
      </p>
      <h1>{languageId === null ? 'Add a language' : lang.name}</h1>

      <div className="form language-form">
        {languageId === null && predefined.length > 0 && (
          <label>
            Start from
            <select defaultValue="" onChange={(e) => startFrom(e.target.value)}>
              <option value="">Blank</option>
              {predefined.map((n) => (
                <option key={n}>{n}</option>
              ))}
            </select>
          </label>
        )}
        <label>
          Name
          <input value={lang.name} maxLength={40} onChange={(e) => set({ name: e.target.value })} />
        </label>
        <label>
          Parse as
          <select value={lang.parserType} onChange={(e) => set({ parserType: e.target.value })}>
            {parsers.map((p) => (
              <option key={p.type} value={p.type}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <label className="inline">
          <input type="checkbox" checked={lang.showRomanization} onChange={(e) => set({ showRomanization: e.target.checked })} />
          Show a pronunciation field
        </label>
        <label className="inline">
          <input type="checkbox" checked={lang.rightToLeft} onChange={(e) => set({ rightToLeft: e.target.checked })} />
          Right to left
        </label>

        <h2>Dictionaries</h2>
        <p className="muted">
          Use [LUTE] where the word goes. The first active dictionary of each kind opens first. "Embedded" shows inside the app; sites that refuse
          that need "Pop-up window".
        </p>
        <table className="dicts">
          <thead>
            <tr>
              <th>For</th>
              <th>Show as</th>
              <th>Web address</th>
              <th>Active</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {lang.dictionaries.map((d, i) => (
              <tr key={i}>
                <td>
                  <select value={d.useFor} onChange={(e) => setDict(i, { useFor: e.target.value as DictionarySetting['useFor'] })}>
                    <option value="terms">Terms</option>
                    <option value="sentences">Sentences</option>
                  </select>
                </td>
                <td>
                  <select value={d.dictType} onChange={(e) => setDict(i, { dictType: e.target.value as DictionarySetting['dictType'] })}>
                    <option value="embeddedhtml">Embedded</option>
                    <option value="popuphtml">Pop-up window</option>
                  </select>
                </td>
                <td>
                  <input className="wide" value={d.url} onChange={(e) => setDict(i, { url: e.target.value })} />
                </td>
                <td>
                  <input type="checkbox" checked={d.active} onChange={(e) => setDict(i, { active: e.target.checked })} />
                </td>
                <td className="row-inline">
                  <button className="secondary small icon" disabled={i === 0} onClick={() => move(i, -1)} aria-label="Move up">
                    ↑
                  </button>
                  <button className="secondary small icon" disabled={i === lang.dictionaries.length - 1} onClick={() => move(i, 1)} aria-label="Move down">
                    ↓
                  </button>
                  <button className="secondary small icon" onClick={() => set({ dictionaries: lang.dictionaries.filter((_, j) => j !== i) })} aria-label="Remove">
                    ✕
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div>
          <button className="secondary" onClick={() => set({ dictionaries: [...lang.dictionaries, BLANK_DICTIONARY] })}>
            Add a dictionary
          </button>
        </div>

        <h2>Reading rules</h2>
        <label>
          Character substitutions
          <input value={lang.characterSubstitutions} onChange={(e) => set({ characterSubstitutions: e.target.value })} />
        </label>
        <label>
          Split sentences at
          <input value={lang.regexpSplitSentences} onChange={(e) => set({ regexpSplitSentences: e.target.value })} />
        </label>
        <label>
          Split sentence exceptions
          <input value={lang.exceptionsSplitSentences} onChange={(e) => set({ exceptionsSplitSentences: e.target.value })} />
        </label>
        <label>
          Word characters
          <input value={lang.wordCharacters} onChange={(e) => set({ wordCharacters: e.target.value })} />
        </label>

        {error && <p className="error">{error}</p>}
        {saved && <p className="muted">Saved.</p>}
        <div className="actions">
          <button onClick={save}>{languageId === null ? 'Add language' : 'Save'}</button>
          {languageId !== null && (
            <button className="danger" onClick={remove}>
              Delete language
            </button>
          )}
        </div>
      </div>
    </>
  )
}
