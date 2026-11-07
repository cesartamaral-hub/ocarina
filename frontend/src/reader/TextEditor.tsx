import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import {
  countMatches,
  isDirty,
  nextMatch,
  pageAt,
  PAGE_BREAK,
  paragraphCount,
  replaceAll,
  splitPages,
  wordCount,
} from './editing'

// Editing the whole material as one long text, in the same font and size as the reading text so what you edit looks like what you
// read. Pages end at "~~~ page break ~~~" lines (add, move or delete them like any line). A bar stays at the bottom with Save and Cancel.
export function TextEditor({
  value,
  original,
  onChange,
  title,
  originalTitle,
  onTitle,
  onSave,
  onCancel,
  language,
  rightToLeft,
  startPage,
  audioWarning,
  translationWarning,
  saving,
}: {
  value: string
  original: string
  onChange: (text: string) => void
  title: string
  originalTitle: string
  onTitle: (title: string) => void
  onSave: () => void
  onCancel: () => void
  language?: string
  rightToLeft: boolean
  startPage: number // the page the reader was on: the caret starts there
  audioWarning: boolean
  translationWarning: boolean
  saving: boolean
}) {
  const field = useRef<HTMLTextAreaElement>(null)
  const [caret, setCaret] = useState(0)
  const [finding, setFinding] = useState(false)
  const [find, setFind] = useState('')
  const [replacement, setReplacement] = useState('')
  const [matchCase, setMatchCase] = useState(false)
  const dirty = isDirty(value, original) || title.trim() !== originalTitle
  const pages = splitPages(value).length
  const canSave = dirty && !saving && pages > 0 && title.trim() !== ''

  // Start at the page being read: the caret goes to the start of that page, and the field scrolls there.
  useEffect(() => {
    const el = field.current
    if (!el) return
    let at = 0
    for (let p = 1; p < startPage; p++) {
      const next = el.value.indexOf(PAGE_BREAK, at)
      if (next < 0) break
      at = next + PAGE_BREAK.length
    }
    el.focus({ preventScroll: true })
    el.setSelectionRange(at, at)
    setCaret(at)
    const line = el.value.slice(0, at).split('\n').length
    const lineHeight = parseFloat(getComputedStyle(el).lineHeight) || 30
    el.closest('.reader-scroll')?.scrollTo({
      top: Math.max(0, el.offsetTop + line * lineHeight - 140),
    })
  }, [startPage])

  // The field grows with its text, so the page scrolls instead of the field.
  useLayoutEffect(() => {
    const el = field.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${el.scrollHeight}px`
  }, [value])

  function insertBreak() {
    const el = field.current
    if (!el) return
    const at = el.selectionStart
    const mark = `\n\n${PAGE_BREAK}\n\n`
    onChange(value.slice(0, at) + mark + value.slice(el.selectionEnd))
    requestAnimationFrame(() => {
      el.focus()
      el.setSelectionRange(at + mark.length, at + mark.length)
    })
  }

  function findNext() {
    const el = field.current
    if (!el || !find) return
    const from =
      el.selectionEnd > el.selectionStart &&
      value.slice(el.selectionStart, el.selectionEnd).toLowerCase() === find.toLowerCase()
        ? el.selectionEnd
        : el.selectionStart
    const at = nextMatch(value, find, from, matchCase)
    if (at < 0) return
    el.focus()
    el.setSelectionRange(at, at + find.length)
    setCaret(at)
    const line = value.slice(0, at).split('\n').length
    const lineHeight = parseFloat(getComputedStyle(el).lineHeight) || 30
    el.closest('.reader-scroll')?.scrollTo({
      top: Math.max(0, el.offsetTop + line * lineHeight - 200),
      behavior: 'smooth',
    })
  }

  const matches = finding ? countMatches(value, find, matchCase) : 0

  return (
    <section className="text-editor" aria-label="Edit text">
      <div className="editor-head">
        <input
          className="editor-title"
          value={title}
          maxLength={200}
          aria-label="Title"
          onChange={(e) => onTitle(e.target.value)}
        />
        <span className="editor-tools">
          <button
            className="secondary small"
            aria-pressed={finding}
            onClick={() => setFinding((f) => !f)}
            title="Find and replace (⌘F)"
          >
            Find
          </button>
          <button className="secondary small" onClick={insertBreak} title="Start a new page at the cursor">
            Add page break
          </button>
        </span>
      </div>
      {finding && (
        <div className="editor-find" role="search">
          <input
            value={find}
            autoFocus
            placeholder="Find"
            aria-label="Find"
            onChange={(e) => setFind(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && findNext()}
          />
          <input
            value={replacement}
            placeholder="Replace with"
            aria-label="Replace with"
            onChange={(e) => setReplacement(e.target.value)}
          />
          <label className="inline">
            <input type="checkbox" checked={matchCase} onChange={(e) => setMatchCase(e.target.checked)} /> Match case
          </label>
          <span className="muted" aria-live="polite">
            {find ? `${matches} found` : ''}
          </span>
          <button className="secondary small" disabled={matches === 0} onClick={findNext}>
            Next
          </button>
          <button
            className="secondary small"
            disabled={matches === 0}
            onClick={() => onChange(replaceAll(value, find, replacement, matchCase))}
          >
            Replace all
          </button>
        </div>
      )}
      <textarea
        ref={field}
        value={value}
        lang={language}
        dir={rightToLeft ? 'rtl' : 'ltr'}
        spellCheck
        aria-label="Text of the material"
        onChange={(e) => {
          onChange(e.target.value)
          setCaret(e.target.selectionStart)
        }}
        onSelect={(e) => setCaret(e.currentTarget.selectionStart)}
        onKeyDown={(e) => {
          if ((e.key === 'Enter' || e.key === 's') && (e.metaKey || e.ctrlKey)) {
            e.preventDefault()
            if (canSave) onSave()
          } else if (e.key === 'f' && (e.metaKey || e.ctrlKey)) {
            e.preventDefault()
            setFinding(true)
          }
        }}
      />
      {dirty && (audioWarning || translationWarning) && (
        <p className="muted">
          Saving changes the text.
          {audioWarning && ' The audio was made from the old text; make it again so the highlighting matches.'}
          {translationWarning &&
            ' Sentences that changed lose their translation until you translate again. If pages move, later pages are affected too.'}
        </p>
      )}
      <div className="editor-bar">
        <span className="muted" aria-live="polite">
          {dirty ? 'Unsaved changes' : 'No changes'} · page {Math.min(pageAt(value, caret), Math.max(pages, 1))} of{' '}
          {pages} · {wordCount(value)} words · {paragraphCount(value)} paragraphs
        </span>
        <span className="editor-actions">
          <button className="secondary" onClick={onCancel}>
            Cancel
          </button>
          <button disabled={!canSave} onClick={onSave} title="Save (⌘S)">
            {saving ? 'Saving…' : 'Save text'}
          </button>
        </span>
      </div>
    </section>
  )
}
