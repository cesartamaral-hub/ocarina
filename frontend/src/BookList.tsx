import { useCallback, useEffect, useState } from 'react'
import { changeBook, getPref, setPref, deleteBook, getBackupsAfterStartup, getBooks, getLanguages, type Book } from './api'
import { BookRow } from './BookRow'
import { sortBooks, SORTS, type SortKey } from './bookStats'
import { Welcome } from './Welcome'

function EditForm({ book, onDone }: { book: Book; onDone: (changed: boolean) => void }) {
  const [title, setTitle] = useState(book.title)
  const [source, setSource] = useState(book.sourceUri)
  const [tags, setTags] = useState(book.tags.join(', '))
  const [error, setError] = useState('')
  async function save() {
    try {
      await changeBook(book.id, {
        title,
        sourceUri: source,
        tags: tags.split(',').map((t) => t.trim()).filter(Boolean),
      })
      onDone(true)
    } catch (e) {
      setError((e as Error).message)
    }
  }
  return (
    <div className="form book-edit">
      <label>
        Title
        <input value={title} maxLength={200} onChange={(e) => setTitle(e.target.value)} />
      </label>
      <label>
        Source (optional)
        <input value={source} onChange={(e) => setSource(e.target.value)} />
      </label>
      <label>
        Tags (comma separated)
        <input value={tags} onChange={(e) => setTags(e.target.value)} />
      </label>
      {error && <p className="error">{error}</p>}
      <div className="actions">
        <button disabled={!title.trim()} onClick={save}>
          Save
        </button>
        <button className="secondary" onClick={() => onDone(false)}>
          Cancel
        </button>
      </div>
    </div>
  )
}

export function BookList() {
  const [books, setBooks] = useState<Book[] | null>(null)
  const [archived, setArchived] = useState(false)
  const [editing, setEditing] = useState<number | null>(null)
  const [tag, setTag] = useState('')
  const [sort, setSort] = useState<SortKey>(() => getPref<SortKey>('books.sort', 'title'))
  const [onlyAudio, setOnlyAudio] = useState(false)
  const [error, setError] = useState('')
  const [firstRun, setFirstRun] = useState(false)
  const [backupWarning, setBackupWarning] = useState('')

  const load = useCallback(
    () => getBooks(archived).then(setBooks, (e) => setError(e.message)),
    [archived],
  )
  useEffect(() => {
    load()
  }, [load])
  // Word counts are made in the background; ask again until every book has its numbers.
  const counting = books?.some((b) => b.indexing) ?? false
  useEffect(() => {
    if (!counting) return
    const timer = window.setInterval(load, 1500)
    return () => window.clearInterval(timer)
  }, [counting, load])
  // A library without languages is new: show the first-run screen (it stays until its steps are done).
  useEffect(() => {
    getLanguages().then((l) => l.length === 0 && setFirstRun(true), () => undefined)
  }, [])
  useEffect(() => {
    getBackupsAfterStartup().then((b) => setBackupWarning(b.warning), () => undefined)
  }, [])

  async function act(work: Promise<unknown>) {
    setError('')
    try {
      await work
      await load()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  function remove(b: Book) {
    const extra = b.hasAudio && b.ocarinaAudio ? ' Its generated audio is deleted too.' : ''
    if (window.confirm(`Delete "${b.title}" and its pages?${extra} Your terms are kept. This cannot be undone.`)) act(deleteBook(b.id))
  }

  if (error && !books) return <p className="error">{error}</p>
  if (!books) return <p className="muted">Loading…</p>
  if (firstRun)
    return (
      <Welcome
        onFinish={() => {
          setFirstRun(false)
          load()
        }}
      />
    )

  const allTags = [...new Set(books.flatMap((b) => b.tags))].sort()
  const shown = sortBooks(books.filter((b) => (!tag || b.tags.includes(tag)) && (!onlyAudio || b.hasAudio)), sort)
  const languages = [...new Set(shown.map((b) => b.language))]
  return (
    <>
      <div className="title-row">
        <h1>{archived ? 'Archived books' : 'Books'}</h1>
        <a href="#/new" className="button">
          Add a book
        </a>
      </div>
      {backupWarning && (
        <p className="error">
          {backupWarning} <a href="#/backups">Open backups</a>
        </p>
      )}
      <div className="controls">
        <label className="inline">
          <input type="checkbox" checked={archived} onChange={(e) => (setBooks(null), setArchived(e.target.checked))} />
          Show archived books
        </label>
        <label className="inline">
          Sort by
          <select
            value={sort}
            onChange={(e) => {
              setSort(e.target.value as SortKey)
              setPref('books.sort', e.target.value)
            }}
          >
            {SORTS.map((o) => (
              <option key={o.key} value={o.key}>
                {o.label}
              </option>
            ))}
          </select>
        </label>
        <label className="inline">
          <input type="checkbox" checked={onlyAudio} onChange={(e) => setOnlyAudio(e.target.checked)} />
          Has audio
        </label>
        {allTags.length > 0 && (
          <label className="inline">
            Tag
            <select value={tag} onChange={(e) => setTag(e.target.value)}>
              <option value="">any</option>
              {allTags.map((t) => (
                <option key={t}>{t}</option>
              ))}
            </select>
          </label>
        )}
      </div>
      {error && <p className="error">{error}</p>}
      {shown.length === 0 && <p className="muted">{archived ? 'No archived books.' : 'No books yet. Add one to start reading.'}</p>}
      {languages.map((lang) => (
        <section key={lang}>
          <h2>{lang}</h2>
          <ul className="books">
            {shown
              .filter((b) => b.language === lang)
              .map((b) => (
                <li key={b.id} className={editing === b.id ? 'editing' : ''}>
                  <BookRow
                    book={b}
                    onEdit={() => setEditing(editing === b.id ? null : b.id)}
                    onArchive={() => act(changeBook(b.id, { archived: !b.archived }))}
                    onDelete={() => remove(b)}
                  />
                  {editing === b.id && (
                    <EditForm
                      book={b}
                      onDone={(changed) => {
                        setEditing(null)
                        if (changed) load()
                      }}
                    />
                  )}
                </li>
              ))}
          </ul>
        </section>
      ))}
    </>
  )
}
