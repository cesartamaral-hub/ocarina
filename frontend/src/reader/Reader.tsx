import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { notify } from '../notices'
import { usePlaybackKeys } from '../playbackKeys'
import {
  bulkStatus,
  finishPage,
  getPage,
  getPageText,
  getPref,
  openExternal,
  putPageText,
  setPref,
  type Item,
  type ReaderPage,
  type Term,
} from '../api'
import { dictUrl } from './dictUrl'
import { SentenceBlock } from './SentenceBlock'
import { AudioPanel } from './AudioPanel'
import { languageCode } from '../typography'
import { classify } from './selection'
import { KeyHelp } from './KeyHelp'
import { ReaderLayout } from './ReaderLayout'
import { ReaderToolbar } from './ReaderToolbar'
import { actionFor, statusForKey, statusKeyLabel } from '../shortcutKeys'
import { STATUS_BUTTONS, statusName } from './statuses'
import { TermPanel, type Target } from './TermPanel'
import { useAudioFollow } from './useAudioFollow'
import { useHoverCard } from './useHoverCard'

export function Reader({ bookId, pageNumber }: { bookId: number; pageNumber: number }) {
  const [page, setPage] = useState<ReaderPage | null>(null)
  const [error, setError] = useState('')
  const [help, setHelp] = useState(false)
  const [selected, setSelected] = useState<Target | null>(null)
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)
  const [multi, setMulti] = useState<Set<number>>(new Set())
  const [reloadKey, setReloadKey] = useState(0)
  const [editing, setEditing] = useState<string | null>(null)
  const [follow, setFollow] = useState(true)
  const [highlights, setHighlights] = useState(() => getPref('highlights', true))
  const toggleHighlights = useCallback(() => {
    setHighlights((on) => {
      setPref('highlights', !on)
      return !on
    })
  }, [])
  const hoverCard = useHoverCard()
  const shownPage = useRef(0)
  const [audioVersion, setAudioVersion] = useState(0) // bumped when another audio version is picked
  const audio = useAudioFollow(bookId, page, follow, audioVersion)
  usePlaybackKeys(audio.audioRef, audio.starts)

  useEffect(() => {
    const run = { alive: true }
    getPage(bookId, pageNumber).then(
      (p) => {
        if (!run.alive) return
        setPage(p)
        setError('')
        if (shownPage.current !== pageNumber) {
          setSelected(null)
          setMulti(new Set())
          window.scrollTo(0, 0)
        }
        shownPage.current = pageNumber
      },
      (e) => run.alive && setError(e.message),
    )
    return () => {
      run.alive = false
    }
  }, [bookId, pageNumber, reloadKey])

  const flat = useMemo(() => page?.paragraphs.flat(2) ?? [], [page])

  // Same term, anywhere on the page, gets the new status at once.
  const applyStatus = useCallback((termId: number, status: number) => {
    setPage((p) =>
      p && {
        ...p,
        paragraphs: p.paragraphs.map((para) =>
          para.map((sent) => sent.map((it) => (it.termId === termId ? { ...it, status } : it))),
        ),
      },
    )
  }, [])
  const termChanged = useCallback((termId: number) => hoverCard.forget(termId), [hoverCard])
  const termCreated = useCallback((term: Term) => {
    // A new phrase changes how the page is cut into items, so ask the server for the page again.
    setSelected((s) => s && { ...s, termId: term.id, text: term.text })
    setReloadKey((k) => k + 1)
  }, [])

  const selectRange = useCallback(
    (from: number, to: number, asText = false) => {
      const [lo, hi] = from <= to ? [from, to] : [to, from]
      const range = flat.filter((it) => it.index >= lo && it.index <= hi)
      const picked = classify(range)
      if (!picked) return false
      setSelected(
        picked.kind === 'phrase' && !asText
          ? { termId: null, text: picked.text, sentence: picked.sentence }
          : { termId: null, text: picked.text, sentence: picked.sentence, kind: 'text', span: [lo, hi] },
      )
      setSelectedIndex(null)
      return true
    },
    [flat],
  )

  function onWordClick(e: React.MouseEvent, it: Item) {
    if (e.metaKey || e.ctrlKey) {
      if (it.termId === null) return
      const id = it.termId
      setMulti((m) => {
        const next = new Set(m)
        if (next.has(id)) next.delete(id)
        else next.add(id)
        return next
      })
      return
    }
    if (e.altKey) {
      const own = flat.filter((x) => x.sentence === it.sentence)
      if (own.length && selectRange(own[0].index, own[own.length - 1].index, true)) return
    }
    if (e.shiftKey && selectedIndex !== null && selectRange(selectedIndex, it.index)) return
    setSelected({ termId: it.termId, text: it.text, sentence: it.sentence })
    setSelectedIndex(it.index)
  }

  // Dragging across several words makes a phrase.
  function onMouseUp() {
    const sel = window.getSelection()
    if (!sel || sel.isCollapsed) return
    const index = (n: Node | null) => {
      const el = n instanceof Element ? n : n?.parentElement
      const v = el?.closest('[data-i]')?.getAttribute('data-i')
      return v === null || v === undefined ? null : Number(v)
    }
    const a = index(sel.anchorNode)
    const f = index(sel.focusNode)
    if (a !== null && f !== null && selectRange(a, f)) sel.removeAllRanges()
  }

  // Page turning, and clearing the selection, from the keyboard.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement).tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || e.metaKey || e.ctrlKey || e.altKey) return
      const action = actionFor(e)?.id
      if (action === 'clear') {
        setSelected(null)
        setMulti(new Set())
        setHelp(false)
      } else if (action === 'help') {
        setHelp((h) => !h)
      } else if (action === 'highlights') {
        toggleHighlights()
      } else if (action === 'prevPage' && pageNumber > 1) {
        window.location.hash = `#/book/${bookId}/read/${pageNumber - 1}`
      } else if (action === 'nextPage' && page && pageNumber < page.pageCount) {
        window.location.hash = `#/book/${bookId}/read/${pageNumber + 1}`
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [bookId, pageNumber, page, toggleHighlights])

  // The status keys apply to all ctrl-clicked words when there are any.
  const applyMulti = useCallback(
    async (status: number) => {
      const ids = [...multi]
      if (ids.length === 0) return
      try {
        await bulkStatus(ids, status)
        ids.forEach((id) => {
          applyStatus(id, status)
          hoverCard.forget(id)
        })
        setMulti(new Set())
        notify(`${ids.length} ${ids.length === 1 ? 'word' : 'words'} set to ${statusName(status)}`)
      } catch (e) {
        setError((e as Error).message)
      }
    },
    [multi, applyStatus, hoverCard],
  )
  useEffect(() => {
    if (multi.size === 0) return
    function onKey(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement).tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || e.metaKey || e.ctrlKey || e.altKey) return
      const status = statusForKey(e)
      if (status !== undefined) {
        e.preventDefault()
        applyMulti(status)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [multi, applyMulti])

  async function finish(restAsKnown: boolean) {
    if (!page) return
    try {
      await finishPage(page.bookId, page.page, restAsKnown)
      notify(restAsKnown ? 'Page finished, the rest marked as known' : 'Page finished')
      window.location.hash =
        page.page < page.pageCount ? `#/book/${bookId}/read/${page.page + 1}` : `#/book/${bookId}`
    } catch (e) {
      setError((e as Error).message)
    }
  }

  async function startEditing() {
    if (!page) return
    try {
      setEditing((await getPageText(bookId, page.page)).text)
    } catch (e) {
      setError((e as Error).message)
    }
  }
  async function saveEditing() {
    if (!page || editing === null) return
    try {
      await putPageText(bookId, page.page, editing)
      notify('Text saved')
      setEditing(null)
      setSelected(null)
      hoverCard.forgetAll()
      setReloadKey((k) => k + 1)
    } catch (e) {
      setError((e as Error).message)
    }
  }

  if (error && !page) return <p className="error">{error}</p>
  if (!page) return <p className="muted">Loading…</p>

  const sentenceText = (sentence: number) =>
    page.paragraphs
      .flat()
      .filter((s) => s[0]?.sentence === sentence)
      .flat()
      .map((i) => i.text)
      .join('')
      .trim()

  return (
    <>
      <ReaderLayout
        selectionKey={selected ? (selected.termId !== null ? `term:${selected.termId}` : `text:${selected.text}`) : null}
        onCloseDrawer={() => {
          setSelected(null)
          setMulti(new Set())
        }}
        main={
          <>
            {audio.audioInfo?.hasAudio && (
              <AudioPanel
                bookId={bookId}
                language={page.language.name}
                audioVersion={audioVersion}
                onVersionChanged={() => setAudioVersion((v) => v + 1)}
                audio={audio}
                follow={follow}
                onFollowChange={setFollow}
              />
            )}
            <div className="reader-column">
              <ReaderToolbar
                bookId={bookId}
                title={page.title}
                page={page.page}
                pageCount={page.pageCount}
                highlights={highlights}
                onToggleHighlights={toggleHighlights}
                onEdit={startEditing}
                onHelp={() => setHelp(true)}
              />
              {help && <KeyHelp onClose={() => setHelp(false)} />}
              {error && <p className="error">{error}</p>}
              {editing !== null ? (
          <div className="edit-text">
            <textarea rows={18} value={editing} onChange={(e) => setEditing(e.target.value)} />
            {audio.timings && (
              <p className="muted">The audio was made from the old text. Regenerate it afterwards.</p>
            )}
            <div className="pager">
              <button onClick={saveEditing}>Save text</button>
              <button className="secondary" onClick={() => setEditing(null)}>
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <>
            <article className={highlights ? '' : 'plain'} dir={page.language.rightToLeft ? 'rtl' : 'ltr'} lang={languageCode(page.language.name)} onMouseUp={onMouseUp}>
              {page.paragraphs
                .filter((para) => para.length > 0) // blank lines come as empty paragraphs
                .map((para, pi) => (
                  <p key={pi}>
                    {para.map((sent, si) => (
                      <span
                        key={si}
                        data-sent={sent[0]?.sentence}
                        className={`sentence${sent[0]?.sentence === audio.playing ? ' playing' : ''}${selected?.sentence === sent[0]?.sentence ? ' active' : ''}`}
                      >
                        {sent.map((it) =>
                          it.isWord ? (
                            <span
                              key={it.index}
                              data-i={it.index}
                              className={`w s${it.status}${
                                selected?.termId !== null && selected?.termId === it.termId ? ' sel' : ''
                              }${it.termId !== null && multi.has(it.termId) ? ' multi' : ''}${
                                selected?.span && it.index >= selected.span[0] && it.index <= selected.span[1] ? ' in-span' : ''
                              }`}
                              onClick={(e) => onWordClick(e, it)}
                              onMouseEnter={(e) => hoverCard.start(it, e.currentTarget, page.language.id)}
                              onMouseLeave={hoverCard.end}
                            >
                              {it.display}
                            </span>
                          ) : (
                            <span key={it.index} data-i={it.index}>
                              {it.display}
                            </span>
                          ),
                        )}
                      </span>
                    ))}
                  </p>
                ))}
            </article>
            <nav className="pager">
              <button
                className="secondary"
                disabled={page.page <= 1}
                onClick={() => (window.location.hash = `#/book/${bookId}/read/${page.page - 1}`)}
              >
                ← Previous
              </button>
              <button onClick={() => finish(false)}>
                {page.page < page.pageCount ? 'Finish page → next' : 'Finish book'}
              </button>
              <button className="secondary" onClick={() => finish(true)} title="Unknown words become well-known">
                Finish, rest as known →
              </button>
            </nav>
            <p className="muted">
              Arrow keys turn pages. Drag over several words (or shift-click) to make a phrase. Ctrl/⌘-click
              words to set their status together.
            </p>
          </>
              )}
            </div>
          </>
        }
        side={
          selected?.kind === 'text' ? (
          <section className="text-selection" key={`text:${selected.text}`}>
            <h2>Selected text</h2>
            <SentenceBlock
              languageId={page.language.id}
              text={selected.text}
              playStart={audio.startOf(selected.sentence)}
              onPlay={audio.playAt}
              noun="text"
              onOpenInBrowser={
                page.language.sentenceDictionaries[0] ? () => openExternal(dictUrl(page.language.sentenceDictionaries[0], selected.text)).catch((e) => setError(e.message)) : undefined
              }
            />
            <button className="secondary" onClick={() => setSelected({ termId: null, text: selected.text, sentence: selected.sentence })}>
              Save as phrase anyway
            </button>
          </section>
        ) : selected ? (
          <TermPanel
            key={selected.termId ?? `new:${selected.text}`}
            page={page}
            target={selected}
            sentenceText={sentenceText(selected.sentence)}
            playStart={audio.startOf(selected.sentence)}
            onPlay={audio.playAt}
            keysEnabled={multi.size === 0}
            onStatus={applyStatus}
            onChanged={termChanged}
            onCreated={termCreated}
            onError={setError}
          />
        ) : (
          <p className="muted">Click a word. Then press 1–5, w (well known) or i (ignore).</p>
        )
        }
      />

      {multi.size > 0 && (
        <div className="bulk-bar">
          <span>
            {multi.size} word{multi.size === 1 ? '' : 's'} selected
          </span>
          {STATUS_BUTTONS.map((b) => (
            <button key={b.status} title={`${b.title} (${statusKeyLabel(b.status)})`} className={`st s${b.status}`} onClick={() => applyMulti(b.status)}>
              {b.label}
            </button>
          ))}
          <button className="secondary" onClick={() => setMulti(new Set())}>
            Clear
          </button>
        </div>
      )}

      {hoverCard.card}
    </>
  )
}
