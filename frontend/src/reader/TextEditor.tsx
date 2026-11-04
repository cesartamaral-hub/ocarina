import { useEffect, useLayoutEffect, useRef } from 'react'
import { isDirty, paragraphCount, wordCount } from './editing'

// Editing the text of a page: a wide, tall field in the same font and size as the reading text, so what you
// edit looks like what you read, and a bar that stays at the bottom of the window with Save and Cancel.
export function TextEditor({
  value,
  original,
  onChange,
  onSave,
  onCancel,
  language,
  rightToLeft,
  page,
  pageCount,
  audioWarning,
  saving,
}: {
  value: string
  original: string
  onChange: (text: string) => void
  onSave: () => void
  onCancel: () => void
  language?: string
  rightToLeft: boolean
  page: number
  pageCount: number
  audioWarning: boolean
  saving: boolean
}) {
  const field = useRef<HTMLTextAreaElement>(null)
  const dirty = isDirty(value, original)

  useEffect(() => field.current?.focus({ preventScroll: true }), [])
  // The field grows with its text, so the page scrolls instead of the field.
  useLayoutEffect(() => {
    const el = field.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${el.scrollHeight}px`
  }, [value])

  return (
    <section className="text-editor" aria-label="Edit text">
      <h2>
        Edit text <span className="muted">· page {page} of {pageCount}</span>
      </h2>
      <textarea
        ref={field}
        value={value}
        lang={language}
        dir={rightToLeft ? 'rtl' : 'ltr'}
        spellCheck
        aria-label="Text of the page"
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
            e.preventDefault()
            if (dirty && !saving) onSave()
          }
        }}
      />
      {audioWarning && <p className="muted">The audio was made from the old text. After saving, make it again so the highlighting matches.</p>}
      <div className="editor-bar">
        <span className="muted" aria-live="polite">
          {dirty ? 'Unsaved changes' : 'No changes'} · {wordCount(value)} words · {paragraphCount(value)} paragraphs
        </span>
        <span className="editor-actions">
          <button className="secondary" onClick={onCancel}>
            Cancel
          </button>
          <button disabled={!dirty || saving} onClick={onSave} title="Save (⌘↵)">
            {saving ? 'Saving…' : 'Save text'}
          </button>
        </span>
      </div>
    </section>
  )
}
