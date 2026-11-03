import { useCallback, useEffect, useRef, useState } from 'react'
import {
  deleteImage,
  getReferences,
  getTerm,
  lookupTerm,
  openExternal,
  saveTerm,
  setTermStatus,
  uploadImage,
  type Dictionary,
  type ReaderPage,
  type References,
  type Term,
} from '../api'
import { notify } from '../notices'
import { STATUS_BUTTONS } from './statuses'

// Dictionary urls contain [LUTE] (older ones ###) where the word goes; a leading * only marked
// "open as popup" in Lute.
function dictUrl(d: Dictionary, text: string): string {
  const word = encodeURIComponent(text)
  return d.url.replace(/^\*/, '').replace('[LUTE]', word).replace('###', word)
}

function dictName(d: Dictionary): string {
  try {
    return new URL(dictUrl(d, 'x')).hostname.replace(/^www\./, '')
  } catch {
    return 'dictionary'
  }
}

// Dictionary types Lute shows inside its own window; the others are meant for a separate window.
const canEmbed = (d: Dictionary) => d.dicttype.startsWith('embedded')

export type Target = { termId: number | null; text: string; sentence: number }

export function TermPanel({
  page,
  target,
  sentenceText,
  playStart,
  onPlay,
  keysEnabled,
  onStatus,
  onChanged,
  onCreated,
  onError,
}: {
  page: ReaderPage
  target: Target
  sentenceText: string
  playStart?: number
  onPlay: (seconds: number) => void
  keysEnabled: boolean
  onStatus: (termId: number, status: number) => void
  onChanged: (termId: number) => void
  onCreated: (term: Term) => void
  onError: (message: string) => void
}) {
  const [term, setTerm] = useState<Term | null>(null)
  const [saved, setSaved] = useState(true)
  const [viewing, setViewing] = useState<Dictionary | null>(null)
  const [refs, setRefs] = useState<References | null>(null)
  const [showRefs, setShowRefs] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const load = target.termId ? getTerm(target.termId) : lookupTerm(page.language.id, target.text)
    load.then(setTerm, (e) => onError(e.message))
  }, [target.termId, target.text, page.language.id, onError])

  const persist = useCallback(
    async (t: Term, status: number) => {
      const result = await saveTerm({
        id: t.id ?? undefined,
        languageId: t.languageId,
        text: t.text,
        status,
        translation: t.translation,
        romanization: t.romanization,
        tags: t.tags,
        parents: t.parents,
      })
      setTerm(result)
      setSaved(true)
      if (t.id === null) onCreated(result)
      else {
        onStatus(result.id!, result.status)
        onChanged(result.id!)
      }
    },
    [onCreated, onStatus, onChanged],
  )

  const changeStatus = useCallback(
    async (status: number) => {
      if (!term) return
      try {
        if (term.id === null) {
          await persist(term, status)
          return
        }
        await setTermStatus(term.id, status)
        setTerm({ ...term, status })
        onStatus(term.id, status)
        onChanged(term.id)
      } catch (e) {
        onError((e as Error).message)
      }
    },
    [term, persist, onStatus, onChanged, onError],
  )

  // Keyboard: 1-5, w, i, as long as no text field has focus.
  useEffect(() => {
    if (!keysEnabled) return
    function onKey(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement).tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || e.metaKey || e.ctrlKey || e.altKey) return
      const b = STATUS_BUTTONS.find((s) => s.key === e.key.toLowerCase())
      if (b) {
        e.preventDefault()
        changeStatus(b.status)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [changeStatus, keysEnabled])

  useEffect(() => {
    if (!showRefs || refs || !term?.id) return
    getReferences(term.id).then(setRefs, (e) => onError(e.message))
  }, [showRefs, refs, term?.id, onError])

  if (!term) return <p className="muted">Loading…</p>

  const edit = (patch: Partial<Term>) => {
    setTerm({ ...term, ...patch })
    setSaved(false)
  }
  const save = () =>
    persist(term, term.status === 0 ? 1 : term.status).catch((e) => onError((e as Error).message))
  const openOutside = (d: Dictionary, text: string) =>
    openExternal(dictUrl(d, text)).catch((e) => onError(e.message))

  async function pickImage(file: File | undefined) {
    if (!file || !term?.id) return
    try {
      const { image } = await uploadImage(term.id, file)
      setTerm({ ...term, image })
      onChanged(term.id)
      notify('Picture added')
    } catch (e) {
      onError((e as Error).message)
    }
  }
  async function removeImage() {
    if (!term?.id) return
    await deleteImage(term.id)
    setTerm({ ...term, image: null })
    onChanged(term.id)
    notify('Picture removed')
  }

  const isNew = term.id === null
  return (
    <div className="term">
      <h2>{term.displayText}</h2>
      {isNew && <p className="muted">New phrase. Pick a status or fill it in, then save.</p>}
      <div className="statuses">
        {STATUS_BUTTONS.map((b) => (
          <button
            key={b.status}
            title={b.title}
            className={`st s${b.status}${term.status === b.status && !isNew ? ' on' : ''}`}
            onClick={() => changeStatus(b.status)}
          >
            {b.label}
          </button>
        ))}
      </div>

      <div className="dicts">
        {page.language.dictionaries.map((d, i) => (
          <span key={i} className="dict">
            <button
              className={`secondary${viewing === d ? ' on' : ''}`}
              onClick={() => (canEmbed(d) ? setViewing(viewing === d ? null : d) : openOutside(d, term.displayText))}
            >
              {dictName(d)}
            </button>
            {canEmbed(d) && (
              <button className="secondary" title="Open in browser" onClick={() => openOutside(d, term.displayText)}>
                ↗
              </button>
            )}
          </span>
        ))}
        {sentenceText && page.language.sentenceDictionaries[0] && (
          <button className="secondary" onClick={() => openOutside(page.language.sentenceDictionaries[0], sentenceText)}>
            Translate sentence ↗
          </button>
        )}
        {playStart !== undefined && (
          <button className="secondary" onClick={() => onPlay(playStart)}>
            ▶ Play sentence
          </button>
        )}
      </div>
      {viewing && (
        <div className="dict-view">
          <iframe
            title={dictName(viewing)}
            src={dictUrl(viewing, term.displayText)}
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
            referrerPolicy="no-referrer"
          />
          <p className="muted">
            Blank? This site doesn't allow being shown here.{' '}
            <a
              href={dictUrl(viewing, term.displayText)}
              onClick={(e) => {
                e.preventDefault()
                openOutside(viewing, term.displayText)
              }}
            >
              Open in browser
            </a>
          </p>
        </div>
      )}

      <label>
        Translation
        <textarea rows={3} value={term.translation} onChange={(e) => edit({ translation: e.target.value })} />
      </label>
      {page.language.showRomanization && (
        <label>
          Romanization
          <input value={term.romanization} onChange={(e) => edit({ romanization: e.target.value })} />
        </label>
      )}
      <label>
        Tags (comma separated)
        <input
          value={term.tags.join(', ')}
          onChange={(e) => edit({ tags: e.target.value.split(',').map((t) => t.trimStart()) })}
        />
      </label>
      <label>
        Parent words (comma separated)
        <input
          value={term.parents.join(', ')}
          onChange={(e) => edit({ parents: e.target.value.split(',').map((t) => t.trimStart()) })}
        />
      </label>
      <button onClick={save} disabled={saved}>
        {saved ? 'Saved' : 'Save'}
      </button>

      {term.components.length > 0 && (
        <div>
          <h3>Words in this phrase</h3>
          <ul className="components">
            {term.components.map((c) => (
              <li key={c.id}>
                <span className={`chip s${c.status}`}>{c.text}</span> {c.translation}
              </li>
            ))}
          </ul>
        </div>
      )}

      {!isNew && (
        <div>
          <h3>Picture</h3>
          {term.image && <img className="term-image" src={term.image} alt={term.displayText} />}
          <div className="dicts">
            <button className="secondary" onClick={() => fileInput.current?.click()}>
              {term.image ? 'Change picture' : 'Add picture'}
            </button>
            <button
              className="secondary"
              onClick={() =>
                openExternal(`https://www.bing.com/images/search?q=${encodeURIComponent(term.displayText)}`).catch((e) =>
                  onError(e.message),
                )
              }
            >
              Find pictures
            </button>
            {term.image && (
              <button className="secondary" onClick={removeImage}>
                Remove
              </button>
            )}
          </div>
          <div
            className="paste-target"
            tabIndex={0}
            onPaste={(e) => {
              const file = [...e.clipboardData.files].find((f) => f.type.startsWith('image/'))
              if (file) {
                e.preventDefault()
                pickImage(file)
              }
            }}
          >
            Copy a picture from your browser, click here and paste it (⌘V).
          </div>
          <input
            ref={fileInput}
            type="file"
            accept="image/png,image/jpeg,image/gif,image/webp"
            hidden
            onChange={(e) => {
              pickImage(e.target.files?.[0])
              e.target.value = ''
            }}
          />
        </div>
      )}

      {!isNew && (
        <div>
          <button className="secondary" onClick={() => setShowRefs(!showRefs)}>
            {showRefs ? 'Hide other examples' : 'Show other examples'}
          </button>
          {showRefs && !refs && <p className="muted">Searching…</p>}
          {showRefs && refs && <ReferenceList refs={refs} />}
        </div>
      )}

      {sentenceText && <p className="muted sentence-preview">{sentenceText}</p>}
    </div>
  )
}

function ReferenceList({ refs }: { refs: References }) {
  const groups = [
    { name: '', items: refs.term },
    ...refs.children.map((g) => ({ name: `Child: ${g.term}`, items: g.references })),
    ...refs.parents.map((g) => ({ name: `Parent: ${g.term}`, items: g.references })),
  ].filter((g) => g.items.length > 0)
  if (groups.length === 0) return <p className="muted">No other examples in pages you have read.</p>
  return (
    <div className="refs">
      {groups.map((g, gi) => (
        <div key={gi}>
          {g.name && <h3>{g.name}</h3>}
          {g.items.map((r, ri) => (
            <p key={ri} className="ref">
              <a href={`#/book/${r.bookId}/read/${r.page}`}>{r.title}</a>
              <br />
              {r.sentence.map((p, pi) => (p.bold ? <b key={pi}>{p.text}</b> : <span key={pi}>{p.text}</span>))}
            </p>
          ))}
        </div>
      ))}
    </div>
  )
}
