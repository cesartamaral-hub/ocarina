import { useEffect, useState } from 'react'
import { createBook, extractFromFile, extractFromUrl, getLanguages, getPref, setPref, type Extracted, type Language } from './api'

const FILE_TYPES = '.txt,.epub,.pdf,.srt,.vtt'

export function NewBook() {
  const [languages, setLanguages] = useState<Language[]>([])
  const [languageId, setLanguageId] = useState(getPref<number>('newBook.languageId', 0))
  const [title, setTitle] = useState('')
  const [text, setText] = useState('')
  const [sourceUri, setSourceUri] = useState('')
  const [audio, setAudio] = useState<File | null>(null)
  const [url, setUrl] = useState('')
  const [note, setNote] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    getLanguages().then(
      (list) => {
        setLanguages(list)
        setLanguageId((cur) => (list.some((l) => l.id === cur) ? cur : (list[0]?.id ?? 0)))
      },
      (e) => setError(e.message),
    )
  }, [])

  async function run(extract: () => Promise<Extracted>) {
    setError('')
    setBusy(true)
    try {
      const got = await extract()
      setTitle(got.title)
      setText(got.text)
      setSourceUri(got.sourceUri)
      setNote(got.note ?? '')
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function save() {
    setError('')
    setBusy(true)
    try {
      const { id } = await createBook({ title, languageId, text, sourceUri, audio })
      setPref('newBook.languageId', languageId)
      window.location.hash = `#/book/${id}`
    } catch (e) {
      setError((e as Error).message)
      setBusy(false)
    }
  }

  return (
    <>
      <p>
        <a href="#/">← Books</a>
      </p>
      <h1>Add a book</h1>

      <section className="panel static">
        <div className="controls">
          <label>
            Open a file (txt, epub, pdf, srt, vtt)
            <input
              type="file"
              accept={FILE_TYPES}
              disabled={busy}
              onChange={(e) => {
                const f = e.target.files?.[0]
                if (f) run(() => extractFromFile(f))
              }}
            />
          </label>
          <label>
            …or a web page
            <span className="row-inline">
              <input value={url} placeholder="https://" onChange={(e) => setUrl(e.target.value)} />
              <button className="secondary" disabled={busy || !url.trim()} onClick={() => run(() => extractFromUrl(url.trim()))}>
                Get text
              </button>
            </span>
          </label>
        </div>
        <p className="muted">Or just paste or type the text below.</p>
      </section>

      <div className="form">
        <label>
          Language
          <select value={languageId} onChange={(e) => setLanguageId(Number(e.target.value))}>
            {languages.map((l) => (
              <option key={l.id} value={l.id}>
                {l.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Title
          <input value={title} maxLength={255} onChange={(e) => setTitle(e.target.value)} />
        </label>
        <label>
          Text
          <textarea rows={14} value={text} onChange={(e) => setText(e.target.value)} />
        </label>
        {note && <p className="muted">{note}</p>}
        <label>
          Source (optional)
          <input value={sourceUri} onChange={(e) => setSourceUri(e.target.value)} />
        </label>
        <label>
          Audio of your own (optional; you can also generate it afterwards)
          <input type="file" accept="audio/*,.m4b,.opus" onChange={(e) => setAudio(e.target.files?.[0] ?? null)} />
        </label>
        {error && <p className="error">{error}</p>}
        <div>
          <button disabled={busy || !title.trim() || !text.trim() || !languageId} onClick={save}>
            Save book
          </button>
        </div>
      </div>
    </>
  )
}
