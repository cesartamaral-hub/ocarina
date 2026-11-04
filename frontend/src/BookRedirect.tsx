import { useEffect, useState } from 'react'
import { getBook } from './api'

// "#/book/12" opens the book in the reader, on the page you were reading.
export function BookRedirect({ bookId }: { bookId: number }) {
  const [error, setError] = useState('')
  useEffect(() => {
    getBook(bookId).then(
      (b) => window.location.replace(`#/book/${bookId}/read/${b.currentPage}`),
      (e) => setError(e.message),
    )
  }, [bookId])
  return error ? (
    <p className="error">
      {error} <a href="#/">Back to your books</a>
    </p>
  ) : (
    <p className="muted">Opening…</p>
  )
}
