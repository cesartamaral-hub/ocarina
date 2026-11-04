import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { notify } from '../notices'
import { usePlaybackKeys } from '../playbackKeys'
import {
  bulkStatusByText,
  finishPage,
  getPage,
  getBook,
  getPageText,
  getPref,
  openExternal,
  putPageText,
  setPref,
  type BookStats,
  type Item,
  type ReaderPage,
  type Term,
} from '../api'
import { dictUrl } from './dictUrl'
import { SentenceBlock } from './SentenceBlock'
import { AudioPanel } from './AudioPanel'
import { languageCode } from '../typography'
import { useEscape } from '../escape'
import { useLeaveGuard } from '../leaveGuard'
import { TextEditor } from './TextEditor'
import { VocabularyPanel } from './VocabularyPanel'
import { TranslationPanel } from './TranslationPanel'
import { effectiveMode, nextMode, pageTranslations, type TranslationMode } from './translationView'
import { useBookTranslation } from './useBookTranslation'
import { pageVocabulary, type NewWord } from './vocabulary'
import { useMediaQuery } from '../useMediaQuery'
import { isDirty } from './editing'
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
  const scroller = useRef<HTMLDivElement>(null)
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)
  // Words picked with Cmd-click, by lowercase text (a word you never opened has no term yet).
  const [multi, setMulti] = useState<Set<string>>(new Set())
  const [dragSpan, setDragSpan] = useState<[number, number] | null>(null)
  const [reloadKey, setReloadKey] = useState(0)
  const [editing, setEditing] = useState<string | null>(null)
  const [original, setOriginal] = useState('')
  const [saving, setSaving] = useState(false)
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
          scroller.current?.scrollTo(0, 0)
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

  // The vocabulary panel on the left: open or closed (remembered) on a wide window; on a narrow one it slides over the text when asked.
  const narrow = useMediaQuery('(max-width: 1099px)')
  const [vocabWide, setVocabWide] = useState(() => getPref<boolean>('reader.vocabOpen', true))
  const [vocabNarrow, setVocabNarrow] = useState(false)
  const vocabOpen = narrow ? vocabNarrow : vocabWide
  const toggleVocab = useCallback(() => {
    if (narrow) return setVocabNarrow((o) => !o)
    setVocabWide(!vocabWide)
    setPref('reader.vocabOpen', !vocabWide)
  }, [narrow, vocabWide])
  useEscape(narrow && vocabNarrow, () => setVocabNarrow(false))
  const vocab = useMemo(() => pageVocabulary(flat), [flat])

  // A translated version of the text, shown beside it or instead of it.
  const tr = useBookTranslation(bookId)
  const [chosenMode, setChosenMode] = useState<TranslationMode>(() => getPref<TranslationMode>('reader.translationMode', 'original'))
  const pageTr = useMemo(() => (page && tr.data ? pageTranslations(page.paragraphs, tr.data.sentences, page.page) : new Map()), [page, tr.data])
  const shown = effectiveMode(chosenMode, pageTr.size > 0)
  const chooseMode = useCallback((m: TranslationMode) => {
    setChosenMode(m)
    setPref('reader.translationMode', m)
  }, [])
  const [pair, setPair] = useState<number | null>(null) // the sentence under the pointer, marked on both sides
  // The book's own numbers come from the server; they follow your status changes a moment after you make them.
  const [bookStats, setBookStats] = useState<BookStats | null | undefined>(undefined)
  const hasPage = page !== null
  useEffect(() => {
    if (!hasPage) return
    let alive = true
    let timer = window.setTimeout(function ask(tries = 0) {
      getBook(bookId).then(
        (b) => {
          if (!alive) return
          setBookStats(b.stats)
          if (b.stats === null && tries < 5) timer = window.setTimeout(() => ask(tries + 1), 2000) // still being counted
        },
        () => undefined,
      )
    }, 1200)
    return () => {
      alive = false
      window.clearTimeout(timer)
    }
  }, [bookId, hasPage, page])

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

  const byIndex = useMemo(() => new Map(flat.map((it) => [it.index, it])), [flat])
  const itemAt = useCallback(
    (target: EventTarget | null) => {
      const el = target instanceof Element ? target.closest('[data-i]') : null
      const v = el?.getAttribute('data-i')
      return v === null || v === undefined ? undefined : byIndex.get(Number(v))
    },
    [byIndex],
  )

  // A click on a word, with what the modifier keys mean.
  // A click on a translated sentence selects the sentence of the original (with its translate and play buttons).
  function selectSentence(sentence: number) {
    const own = flat.filter((x) => x.sentence === sentence)
    if (own.length) selectRange(own[0].index, own[own.length - 1].index, true)
  }

  // A word from the vocabulary panel's list: select it and bring it into view.
  function pickNewWord(w: NewWord) {
    setSelected({ termId: w.termId, text: w.text, sentence: w.sentence })
    setSelectedIndex(w.index)
    document.querySelector(`[data-i="${w.index}"]`)?.scrollIntoView({ block: 'center', behavior: 'smooth' })
    if (narrow) setVocabNarrow(false)
  }

  function clickWord(mods: { meta: boolean; shift: boolean; alt: boolean }, it: Item) {
    if (!it.isWord) return
    if (mods.meta) {
      const key = it.text.toLowerCase()
      setMulti((m) => {
        const next = new Set(m)
        if (next.has(key)) next.delete(key)
        else next.add(key)
        return next
      })
      return
    }
    if (mods.alt) {
      const own = flat.filter((x) => x.sentence === it.sentence)
      if (own.length && selectRange(own[0].index, own[own.length - 1].index, true)) return
    }
    if (mods.shift && selectedIndex !== null && selectRange(selectedIndex, it.index)) return
    setSelected({ termId: it.termId, text: it.text, sentence: it.sentence })
    setSelectedIndex(it.index)
  }

  // Our own mouse handling instead of the browser's text selection and click events, which behave differently
  // in the desktop app's web view: press on a word, drag across the text, release.
  function onMouseDown(e: React.MouseEvent) {
    if (e.button !== 0 || e.ctrlKey) return
    const start = itemAt(e.target)
    if (!start) return
    e.preventDefault() // no native text selection; we draw our own
    window.getSelection()?.removeAllRanges()
    const mods = { meta: e.metaKey, shift: e.shiftKey, alt: e.altKey }
    let last = start.index
    const move = (m: MouseEvent) => {
      const over = itemAt(document.elementFromPoint(m.clientX, m.clientY))
      if (!over || over.index === last) return
      last = over.index
      setDragSpan(last === start.index ? null : [Math.min(start.index, last), Math.max(start.index, last)])
    }
    const up = () => {
      document.removeEventListener('mousemove', move)
      document.removeEventListener('mouseup', up)
      setDragSpan(null)
      if (last !== start.index && selectRange(start.index, last)) return
      clickWord(mods, start)
    }
    document.addEventListener('mousemove', move)
    document.addEventListener('mouseup', up)
  }

  // Esc: leave the editor (asking first if there are changes), else clear the selection, else go back (see escape.ts).
  const cancelEditing = () => {
    if (editing === null || !isDirty(editing, original) || window.confirm('Discard your changes to this text?')) setEditing(null)
  }
  useEscape(editing !== null, cancelEditing)
  useLeaveGuard(editing !== null && isDirty(editing, original), 'Discard your changes to this text?')
  useEscape(editing === null && (selected !== null || multi.size > 0 || help), () => {
    setSelected(null)
    setMulti(new Set())
    setHelp(false)
  })

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
      } else if (action === 'toggleVocab') {
        toggleVocab()
      } else if (action === 'cycleTranslation') {
        chooseMode(nextMode(chosenMode, pageTr.size > 0))
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
  }, [bookId, pageNumber, page, toggleHighlights, toggleVocab, chooseMode, chosenMode, pageTr])

  // The status keys apply to all ctrl-clicked words when there are any.
  const applyMulti = useCallback(
    async (status: number) => {
      if (multi.size === 0 || !page) return
      const count = multi.size
      try {
        await bulkStatusByText(page.language.id, [...multi], status)
        setMulti(new Set())
        setReloadKey((k) => k + 1) // words that had no term now have one
        notify(`${count} ${count === 1 ? 'word' : 'words'} set to ${statusName(status)}`)
      } catch (e) {
        setError((e as Error).message)
      }
    },
    [multi, page],
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
      const text = (await getPageText(bookId, page.page)).text
      setOriginal(text)
      setEditing(text)
    } catch (e) {
      setError((e as Error).message)
    }
  }
  async function saveEditing() {
    if (!page || editing === null) return
    setSaving(true)
    try {
      await putPageText(bookId, page.page, editing)
      notify('Text saved')
      setEditing(null)
      setSelected(null)
      hoverCard.forgetAll()
      setReloadKey((k) => k + 1)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSaving(false)
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
        leftOpen={vocabOpen}
        left={
          <VocabularyPanel
            vocab={vocab}
            page={page.page}
            pageCount={page.pageCount}
            book={bookStats}
            onPick={pickNewWord}
            onClose={() => (narrow ? setVocabNarrow(false) : toggleVocab())}
          />
        }
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
            <div className="reader-scroll" ref={scroller}>
            <ReaderToolbar
              bookId={bookId}
              title={page.title}
              highlights={highlights}
              onToggleHighlights={toggleHighlights}
              vocabOpen={vocabOpen}
              onToggleVocab={toggleVocab}
              translationOn={shown !== 'original'}
              translation={<TranslationPanel tr={tr} mode={shown} onMode={chooseMode} page={page.page} pageHasTranslation={pageTr.size > 0} />}
              onEdit={startEditing}
              onHelp={() => setHelp(true)}
            />
            <div className={`reader-column${shown === 'both' ? ' parallel' : ''}`}>
              {help && <KeyHelp onClose={() => setHelp(false)} />}
              {error && <p className="error">{error}</p>}
              {editing !== null ? (
          <TextEditor
            value={editing}
            original={original}
            onChange={setEditing}
            onSave={saveEditing}
            onCancel={cancelEditing}
            language={languageCode(page.language.name)}
            rightToLeft={page.language.rightToLeft}
            page={page.page}
            pageCount={page.pageCount}
            audioWarning={audio.timings !== null}
            saving={saving}
          />
        ) : (
          <>
            <article className={highlights ? '' : 'plain'} dir={page.language.rightToLeft ? 'rtl' : 'ltr'} lang={languageCode(page.language.name)} onMouseDown={onMouseDown}>
              {page.paragraphs
                .filter((para) => para.length > 0) // blank lines come as empty paragraphs
                .map((para, pi) => {
                  const original = (
                    <p key="o">
                      {para.map((sent, si) => (
                        <span
                          key={si}
                          data-sent={sent[0]?.sentence}
                          className={`sentence${sent[0]?.sentence === audio.playing ? ' playing' : ''}${selected?.sentence === sent[0]?.sentence ? ' active' : ''}${shown === 'both' && sent[0]?.sentence === pair ? ' pair' : ''}`}
                          onMouseEnter={shown === 'both' ? () => setPair(sent[0]?.sentence ?? null) : undefined}
                          onMouseLeave={shown === 'both' ? () => setPair(null) : undefined}
                        >
                          {sent.map((it) =>
                            it.isWord ? (
                              <span
                                key={it.index}
                                data-i={it.index}
                                className={`w s${it.status}${
                                  selected?.termId !== null && selected?.termId === it.termId ? ' sel' : ''
                                }${multi.has(it.text.toLowerCase()) ? ' multi' : ''}${
                                  ((dragSpan ?? selected?.span) && it.index >= (dragSpan ?? selected!.span!)[0] && it.index <= (dragSpan ?? selected!.span!)[1]) ? ' in-span' : ''
                                }`}
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
                  )
                  if (shown === 'original') return <div key={pi} className="para">{original}</div>
                  // The translation of this paragraph: the same sentence numbers, so the sentence being read aloud is marked here too.
                  const translated = (
                    <p key="t" className="tr" lang={tr.data?.target} dir="ltr">
                      {para.map((sent, si) => {
                        const id = sent[0]?.sentence
                        const t = pageTr.get(id)
                        const hasWord = sent.some((i) => i.isWord)
                        if (!hasWord) return null
                        return (
                          <span
                            key={si}
                            data-sent={id}
                            className={`sentence tr-sentence${id === audio.playing ? ' playing' : ''}${selected?.sentence === id ? ' active' : ''}${id === pair ? ' pair' : ''}${t?.stale ? ' tr-stale' : ''}${t ? '' : ' tr-pending'}`}
                            onMouseEnter={() => setPair(id)}
                            onMouseLeave={() => setPair(null)}
                            onClick={() => selectSentence(id)}
                            title={t?.stale ? 'The sentence was edited after this was translated' : 'Click to select this sentence'}
                          >
                            {t ? t.text : shown === 'both' ? '…' : sent.map((i) => i.display).join('')}{' '}
                          </span>
                        )
                      })}
                    </p>
                  )
                  return shown === 'both' ? (
                    <div key={pi} className="para-pair">
                      {original}
                      {translated}
                    </div>
                  ) : (
                    <div key={pi} className="para">
                      {translated}
                    </div>
                  )
                })}
            </article>
            <p className="muted">
              Arrow keys turn pages. Drag over words to make a phrase or select text; ⌘-click words to set their status together; ⌥-click selects a sentence.
            </p>
          </>
              )}
            </div>
            </div>
            <div className="reader-foot">
              {multi.size > 0 && (
                <div className="bulk-bar" role="region" aria-label="Words picked with ⌘-click">
                  <strong>
                    {multi.size} word{multi.size === 1 ? '' : 's'} picked
                  </strong>
                  <span className="bulk-statuses">
                    {STATUS_BUTTONS.map((b) => (
                      <button key={b.status} title={`${b.title} (${statusKeyLabel(b.status)})`} className={`st s${b.status}`} onClick={() => applyMulti(b.status)}>
                        {b.label}
                      </button>
                    ))}
                  </span>
                  <span className="muted bulk-hint">Press 1–5 to set them all · Esc to let go</span>
                  <button className="secondary" onClick={() => setMulti(new Set())}>
                    Clear
                  </button>
                </div>
              )}
            {editing === null && (
              <nav className="page-bar" aria-label="Pages">
                <button className="secondary" disabled={page.page <= 1} onClick={() => (window.location.hash = `#/book/${bookId}/read/${page.page - 1}`)}>
                  ← Previous
                </button>
                <span className="page-count muted">
                  Page {page.page} of {page.pageCount}
                </span>
                <span className="page-actions">
                  <button className="secondary" onClick={() => finish(true)} title="Unknown words become well known">
                    <span className="long">Finish, rest as known</span>
                    <span className="short">Rest as known</span>
                  </button>
                  <button onClick={() => finish(false)}>{page.page < page.pageCount ? 'Finish page →' : 'Finish book'}</button>
                </span>
              </nav>
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

      {hoverCard.card}
    </>
  )
}
