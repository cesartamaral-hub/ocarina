import { useEffect, useState } from 'react'
import { getBooks, type Book } from './api'

export function BookList() {
  const [books, setBooks] = useState<Book[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    getBooks().then(setBooks, (e) => setError(e.message))
  }, [])

  if (error) return <p className="error">{error}</p>
  if (!books) return <p className="muted">Loading…</p>

  const languages = [...new Set(books.map((b) => b.language))]
  return (
    <>
      <div className="title-row">
        <h1>Books</h1>
        <a href="#/new" className="button">
          Add a book
        </a>
      </div>
      {languages.map((lang) => (
        <section key={lang}>
          <h2>{lang}</h2>
          <ul className="books">
            {books
              .filter((b) => b.language === lang)
              .map((b) => (
                <li key={b.id}>
                  <a href={`#/book/${b.id}`}>{b.title}</a>
                  <span className="muted">
                    {b.pages} {b.pages === 1 ? 'page' : 'pages'}
                    {b.hasAudio ? (b.ocarinaAudio ? ' · generated audio' : ' · own audio') : ''}
                  </span>
                </li>
              ))}
          </ul>
        </section>
      ))}
    </>
  )
}
