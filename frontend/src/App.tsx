import { useEffect, useState } from 'react'
import { BookList } from './BookList'
import { BookView } from './BookView'
import { Settings } from './Settings'

// Tiny hash router: "#/" is the book list, "#/book/12" a book.
function useRoute() {
  const [hash, setHash] = useState(window.location.hash)
  useEffect(() => {
    const onChange = () => setHash(window.location.hash)
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  const m = hash.match(/^#\/book\/(\d+)/)
  return { bookId: m ? Number(m[1]) : null, settings: hash === '#/settings' }
}

export default function App() {
  const { bookId, settings } = useRoute()
  return (
    <>
      <header className="top">
        <a href="#/" className="brand">
          Ocarina
        </a>
        <a href="#/settings">Settings</a>
      </header>
      <main>
        {settings ? (
          <Settings />
        ) : bookId === null ? (
          <BookList />
        ) : (
          <BookView key={bookId} bookId={bookId} />
        )}
      </main>
    </>
  )
}
