import { useEffect, useState } from 'react'
import { BookList } from './BookList'
import { BookView } from './BookView'

// Tiny hash router: "#/" is the book list, "#/book/12" a book.
function useRoute() {
  const [hash, setHash] = useState(window.location.hash)
  useEffect(() => {
    const onChange = () => setHash(window.location.hash)
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  const m = hash.match(/^#\/book\/(\d+)/)
  return m ? { bookId: Number(m[1]) } : { bookId: null }
}

export default function App() {
  const { bookId } = useRoute()
  return (
    <>
      <header className="top">
        <a href="#/" className="brand">
          Ocarina
        </a>
      </header>
      <main>{bookId === null ? <BookList /> : <BookView key={bookId} bookId={bookId} />}</main>
    </>
  )
}
