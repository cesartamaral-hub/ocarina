import { useEffect, useState } from 'react'
import { loadPrefs, runDueBackup } from './api'
import { Appearance } from './Appearance'
import { applyAppearance } from './appearanceSettings'
import { onEscapeKey } from './escape'
import { mayFollow } from './leaveGuard'
import { Backups } from './Backups'
import { JobChip } from './JobChip'
import { NoticeList } from './NoticeList'
import { BookList } from './BookList'
import { BookView } from './BookView'
import { LanguageEditor, LanguageList } from './Languages'
import { NewBook } from './NewBook'
import { Reader } from './reader/Reader'
import { Settings } from './Settings'
import { Shortcuts } from './Shortcuts'
import { Tags } from './Tags'
import { Translation } from './Translation'
import { Stats } from './Stats'
import { TermList } from './TermList'

// Tiny hash router: "#/" is the book list, "#/book/12" a book.
function useRoute() {
  const [hash, setHash] = useState(window.location.hash)
  useEffect(() => {
    const onChange = () => setHash(window.location.hash)
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  const m = hash.match(/^#\/book\/(\d+)/)
  const r = hash.match(/^#\/book\/(\d+)\/read\/(\d+)/)
  return {
    bookId: m ? Number(m[1]) : null,
    readPage: r ? Number(r[2]) : null,
    settings: hash === '#/settings',
    newBook: hash === '#/new',
    terms: hash === '#/terms',
    stats: hash === '#/stats',
    tags: hash === '#/tags',
    shortcuts: hash === '#/shortcuts',
    translation: hash === '#/translation',
    appearance: hash === '#/appearance',
    backups: hash === '#/backups',
    languages: hash === '#/languages',
    languageId: hash === '#/languages/new' ? 'new' : (hash.match(/^#\/languages\/(\d+)$/)?.[1] ?? null),
  }
}

function Logo() {
  // The ocarina mark, drawn in the accent colour (source: assets/ocarina-glyph.svg).
  return (
    <svg className="logo" viewBox="170 215 590 620" aria-hidden="true">
      <g transform="matrix(2.045082,0,0,2.045082,-528.293988,-75.915727)" fillRule="evenodd">
        <path d="M347.853,364.474C347.782,362.056 347.323,346.402 351.341,334.442C368.499,283.373 395.856,276.666 393.583,258.492C392.064,246.344 384.006,245.024 390.833,239.939C396.01,236.082 447.117,195.72 448.591,194.629C452.2,191.958 458.09,202.544 464.484,204.547C475.136,207.885 480.557,204.684 487.679,200.832C520.77,182.933 588.46,159.176 623.551,165.192C703.364,178.874 628.282,297.446 555.94,353.989C444.066,441.431 380.786,413.978 365.546,399.45C352.292,386.815 350.296,378.559 347.853,364.474ZM603.855,226.502C602.495,204.853 579.688,208.673 574.951,218.731C564.281,241.385 601.888,252.406 603.855,226.502ZM430.811,351.506C429.497,330.812 406.109,333.315 401.56,344.526C392.087,367.873 428.429,376.658 430.811,351.506ZM475.797,318.5C473.011,295.056 449.023,301.207 445.445,314.486C440.069,334.443 474.078,343.35 475.797,318.5ZM468.163,263.513C470.917,289.32 507.437,276.921 497.121,255.68C491.617,244.347 469.057,242.149 468.163,263.513ZM558.834,258.496C556.996,238.248 534.569,241.29 529.884,251.693C519.517,274.713 557.584,284.927 558.834,258.496ZM524.572,299.097C501.444,296.908 501.913,322.571 514.691,328.043C535.014,336.745 546.95,304.623 524.572,299.097Z" />
        <path d="M389.573,148.795C400.151,146.969 401.424,146.838 417.14,161.898C439.278,183.113 442.511,184.455 441.61,186.576C441.172,187.607 388.784,228.411 384.162,232.011C381.864,233.801 380.857,231.341 376.338,222.581C361.062,192.969 353.366,185.617 358.698,173.59C362.068,165.988 385.015,150.74 389.573,148.795Z" />
      </g>
    </svg>
  )
}

export default function App() {
  const { bookId, readPage, settings, newBook, terms, stats, tags, shortcuts, translation, appearance, backups, languages, languageId } = useRoute()
  // Page width: the reader uses the whole window; the book list and the term list are wider than forms.
  const reading = bookId !== null && readPage !== null
  const onHome = bookId === null && !(settings || newBook || terms || stats || tags || shortcuts || translation || appearance || backups || languages || languageId)
  const medium = terms || onHome
  const [ready, setReady] = useState(false)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => onEscapeKey(e, (hash) => (window.location.hash = hash), () => window.location.hash)
    // A link to another page while text has unsaved changes asks first.
    const onClick = (e: MouseEvent) => {
      const link = e.target instanceof Element ? e.target.closest('a[href]') : null
      if (!mayFollow(link, (question) => window.confirm(question))) {
        e.preventDefault()
        e.stopImmediatePropagation()
      }
    }
    window.addEventListener('keydown', onKey, true)
    window.addEventListener('click', onClick, true)
    return () => {
      window.removeEventListener('keydown', onKey, true)
      window.removeEventListener('click', onClick, true)
    }
  }, [])
  useEffect(() => {
    loadPrefs().then(() => {
      applyAppearance()
      setReady(true)
    })
    runDueBackup()
  }, [])
  return (
    <>
      <header className="top">
        <a href="#/" className="brand">
          <Logo />
          Ocarina
        </a>
        <JobChip />
        <nav>
          <a href="#/terms">Terms</a>
          <a href="#/languages">Languages</a>
          <a href="#/stats">Reading</a>
          <a href="#/settings">Settings</a>
        </nav>
      </header>
      <main className={reading ? 'w-full' : medium ? 'w-medium' : undefined}>
        {!ready ? null : settings ? (
          <Settings />
        ) : tags ? (
          <Tags />
        ) : translation ? (
          <Translation />
        ) : shortcuts ? (
          <Shortcuts />
        ) : appearance ? (
          <Appearance />
        ) : stats ? (
          <Stats />
        ) : backups ? (
          <Backups />
        ) : languages ? (
          <LanguageList />
        ) : languageId ? (
          <LanguageEditor key={languageId} languageId={languageId === 'new' ? null : Number(languageId)} />
        ) : terms ? (
          <TermList />
        ) : newBook ? (
          <NewBook />
        ) : bookId !== null && readPage !== null ? (
          <Reader key={bookId} bookId={bookId} pageNumber={readPage} />
        ) : bookId === null ? (
          <BookList />
        ) : (
          <BookView key={bookId} bookId={bookId} />
        )}
      </main>
      <NoticeList />
    </>
  )
}
