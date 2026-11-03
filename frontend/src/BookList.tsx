import { useCallback, useEffect, useState } from 'react'
import { changeBook, deleteBook, getBackupsAfterStartup, getBooks, type Book } from './api'

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
  const [error, setError] = useState('')
  const [backupWarning, setBackupWarning] = useState('')

  const load = useCallback(
    () => getBooks(archived).then(setBooks, (e) => setError(e.message)),
    [archived],
  )
  useEffect(() => {
    load()
  }, [load])
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

  const allTags = [...new Set(books.flatMap((b) => b.tags))].sort()
  const shown = tag ? books.filter((b) => b.tags.includes(tag)) : books
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
                  <div className="book-row">
                    <div>
                      <a href={`#/book/${b.id}`}>{b.title}</a>
                      {b.tags.length > 0 && <span className="muted"> · {b.tags.join(', ')}</span>}
                    </div>
                    <span className="muted">
                      {b.pages > 1 ? `page ${b.currentPage} of ${b.pages}` : '1 page'}
                      {b.hasAudio ? (b.ocarinaAudio ? ' · generated audio' : ' · own audio') : ''}
                    </span>
                    <span className="row-actions">
                      <a className="button secondary small" href={`#/book/${b.id}/read/${b.currentPage}`}>
                        {b.currentPage > 1 ? 'Continue' : 'Read'}
                      </a>
                      <button className="secondary" onClick={() => setEditing(editing === b.id ? null : b.id)}>
                        Edit
                      </button>
                      <button className="secondary" onClick={() => act(changeBook(b.id, { archived: !b.archived }))}>
                        {b.archived ? 'Unarchive' : 'Archive'}
                      </button>
                      <button className="secondary" onClick={() => remove(b)}>
                        Delete
                      </button>
                    </span>
                  </div>
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
