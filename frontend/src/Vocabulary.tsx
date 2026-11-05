import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  bulkChange,
  getLanguages,
  getReadingLanguage,
  getTags,
  getTermList,
  termExportUrl,
  type BulkChange,
  type Language,
  type ListRow,
  type ReaderPage,
  type TermFilters,
} from './api'
import { useEscape } from './escape'
import { Popover } from './Popover'
import { say } from './pronouncer'
import { ReaderLayout } from './reader/ReaderLayout'
import { STATUS_BUTTONS } from './reader/statuses'
import { TermPanel } from './reader/TermPanel'
import { useAnchoredPopover } from './useAnchoredPopover'
import { CHIPS, DEFAULT_STATUSES, contextParts, languageAbbr, moveActive, timeAgo } from './vocabularyRows'

const PAGE = 100
const SORTS: [string, string][] = [
  ['text', 'Word'],
  ['created', 'Newest first'],
  ['status', 'Status'],
  ['translation', 'Translation'],
  ['language', 'Language'],
]
const DEFAULTS: TermFilters = { language: 0, q: '', statuses: DEFAULT_STATUSES, parentsOnly: false, tag: '', sort: 'text', order: 'asc', page: 1, pageSize: PAGE }

const statusLabel = (s: number) => (s === 99 ? '✓' : s === 98 ? '✕' : String(s))
const onControl = (el: EventTarget | null) => el instanceof Element && el.closest('button, a, summary') !== null
const typing = (el: EventTarget | null) => {
  const e = el as HTMLElement | null
  return !!e && (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.tagName) || e.isContentEditable)
}

function SortMenu({ filters, onSort }: { filters: TermFilters; onSort: (sort: string) => void }) {
  const { anchor, placement, toggle, close } = useAnchoredPopover(200, 'end')
  const current = SORTS.find(([id]) => id === filters.sort)?.[1] ?? 'Word'
  return (
    <>
      <button ref={anchor} className="secondary small" aria-haspopup="menu" aria-expanded={placement !== null} onClick={() => toggle()}>
        Sort: {current} {filters.order === 'asc' ? '▲' : '▼'}
      </button>
      {placement && (
        <Popover anchor={anchor} placement={placement} onClose={close} label="Sort by" role="menu" className="more-menu">
          <ul>
            {SORTS.map(([id, label]) => (
              <li key={id} role="none">
                <button
                  role="menuitemradio"
                  aria-checked={filters.sort === id}
                  onClick={() => {
                    close()
                    onSort(id)
                  }}
                >
                  {filters.sort === id ? '✓ ' : ''}
                  {label}
                  {filters.sort === id ? (filters.order === 'asc' ? ' · A to Z' : ' · Z to A') : ''}
                </button>
              </li>
            ))}
          </ul>
        </Popover>
      )}
    </>
  )
}

export function Vocabulary() {
  const [filters, setFilters] = useState<TermFilters>(DEFAULTS)
  const [typed, setTyped] = useState('')
  const [languages, setLanguages] = useState<Language[]>([])
  const [tags, setTags] = useState<string[]>([])
  const [rows, setRows] = useState<ListRow[]>([])
  const [total, setTotal] = useState<number | null>(null)
  const [counts, setCounts] = useState<Record<string, number>>({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [active, setActive] = useState<number | null>(null) // the word under the cursor: shown in the side panel
  const [panelId, setPanelId] = useState<number | null>(null) // follows `active` after a short pause, so arrowing down does not load every word
  const [checked, setChecked] = useState<Set<number>>(new Set())
  const [tagInput, setTagInput] = useState('')
  const [parentInput, setParentInput] = useState('')
  const [moreOpen, setMoreOpen] = useState(false)
  const [languageInfo, setLanguageInfo] = useState<Record<number, ReaderPage['language']>>({})
  const search = useRef<HTMLInputElement>(null)
  const scroller = useRef<HTMLDivElement>(null)
  const { anchor: moreAnchor, placement: morePlacement, toggle: moreToggle, close: moreClose } = useAnchoredPopover(240, 'end')

  useEffect(() => {
    getLanguages().then(setLanguages, () => undefined)
    getTags().then(setTags, () => undefined)
  }, [])

  // The search box waits for a pause in typing before it asks the server.
  useEffect(() => {
    const timer = setTimeout(() => setFilters((f) => (f.q === typed ? f : { ...f, q: typed })), 250)
    return () => clearTimeout(timer)
  }, [typed])

  const key = JSON.stringify(filters)
  const loaded = useRef(0) // how many rows are on the screen, to ask for them all again after a change
  useEffect(() => {
    loaded.current = rows.length
  })

  // A new filter starts the list again; the answers that arrive after another change are dropped.
  const ask = useRef(0)
  const fetchRows = useCallback(
    async (mode: 'replace' | 'more' | 'refresh') => {
      const mine = ++ask.current
      const f = JSON.parse(key) as TermFilters
      if (mode === 'more') f.page = Math.floor(loaded.current / PAGE) + 1
      if (mode === 'refresh') Object.assign(f, { page: 1, pageSize: Math.min(500, Math.max(PAGE, loaded.current)) })
      setLoading(true)
      try {
        const d = await getTermList(f)
        if (mine !== ask.current) return
        setRows((cur) => (mode === 'more' ? [...cur, ...d.rows.filter((r) => !cur.some((c) => c.id === r.id))] : d.rows))
        setTotal(d.total)
        if (d.counts) setCounts(d.counts)
        setError('')
      } catch (e) {
        if (mine === ask.current) setError((e as Error).message)
      } finally {
        if (mine === ask.current) setLoading(false)
      }
    },
    [key, ask],
  )
  useEffect(() => {
    const timer = setTimeout(() => fetchRows('replace'), 0)
    return () => clearTimeout(timer)
  }, [fetchRows])

  // The next hundred when the end of the list comes near.
  const hasMore = total !== null && rows.length < total
  useEffect(() => {
    const el = scroller.current
    if (!el || !hasMore || loading) return
    const near = () => el.scrollHeight - el.scrollTop - el.clientHeight < 500
    const check = () => near() && fetchRows('more')
    el.addEventListener('scroll', check, { passive: true })
    check() // a short list that does not fill the window yet
    return () => el.removeEventListener('scroll', check)
  }, [hasMore, loading, rows.length, fetchRows])

  function change(patch: Partial<TermFilters>) {
    setFilters((f) => ({ ...f, page: 1, ...patch }))
    setChecked(new Set())
    scroller.current?.scrollTo({ top: 0 })
  }
  const sortBy = (sort: string) => change({ sort, order: filters.sort === sort && filters.order === 'asc' ? 'desc' : 'asc' })
  const toggleStatus = (status: number) =>
    change({ statuses: filters.statuses.includes(status) ? filters.statuses.filter((s) => s !== status) : [...filters.statuses, status].sort((a, b) => a - b) })

  const filtered = filters.q !== '' || filters.language !== 0 || filters.tag !== '' || filters.parentsOnly || filters.statuses.join() !== DEFAULT_STATUSES.join()
  const clearFilters = () => {
    setTyped('')
    change({ ...DEFAULTS })
  }

  // The panel follows the active word.
  useEffect(() => {
    const timer = setTimeout(() => setPanelId(active), active === null ? 0 : 140)
    return () => clearTimeout(timer)
  }, [active])
  useEscape(active !== null, () => setActive(null))
  const activeRow = rows.find((r) => r.id === panelId) ?? null
  useEffect(() => {
    const id = activeRow?.languageId
    if (id === undefined || languageInfo[id]) return
    getReadingLanguage(id).then((info) => setLanguageInfo((cur) => ({ ...cur, [id]: info })), (e) => setError(e.message))
  }, [activeRow?.languageId, languageInfo])

  // What the panel changed about a word shows in the list at once.
  const onStatus = useCallback(
    (termId: number, status: number) => {
      setRows((cur) => (filters.statuses.includes(status) ? cur.map((r) => (r.id === termId ? { ...r, status } : r)) : cur.filter((r) => r.id !== termId)))
      fetchRows('refresh')
    },
    [filters.statuses, fetchRows],
  )
  const onChanged = useCallback(() => fetchRows('refresh'), [fetchRows])

  // The keyboard: arrows move through the words, S or Enter says the word, Space ticks it, / searches.
  const ids = useMemo(() => rows.map((r) => r.id), [rows])
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (typing(e.target) || e.metaKey || e.ctrlKey || e.altKey) return
      if (['ArrowUp', 'ArrowDown', 'Home', 'End'].includes(e.key)) {
        const next = moveActive(ids, active, e.key)
        e.preventDefault()
        if (next !== null) {
          setActive(next)
          document.querySelector(`[data-row="${next}"]`)?.scrollIntoView({ block: 'nearest' })
        }
        return
      }
      const row = rows.find((r) => r.id === active)
      if ((e.key === 's' || e.key === 'S' || e.key === 'Enter') && row && !onControl(e.target)) {
        e.preventDefault()
        if (!e.repeat) say(row.text, row.languageId)
      } else if (e.key === ' ' && row && !onControl(e.target)) {
        e.preventDefault()
        setChecked((c) => {
          const next = new Set(c)
          if (!next.delete(row.id)) next.add(row.id)
          return next
        })
      } else if (e.key === '/') {
        e.preventDefault()
        search.current?.focus()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [ids, active, rows])

  async function apply(change_: Omit<BulkChange, 'ids'>, confirmText?: string) {
    if (confirmText && !window.confirm(confirmText)) return
    try {
      await bulkChange({ ids: [...checked], ...change_ })
      if (change_.delete) setActive(null)
      setChecked(new Set())
      fetchRows('refresh')
    } catch (e) {
      setError((e as Error).message)
    }
  }

  const oneLanguage = filters.language !== 0
  const allChecked = rows.length > 0 && rows.every((r) => checked.has(r.id))
  const everyStatusOff = filters.statuses.length === 0
  const info = activeRow ? languageInfo[activeRow.languageId] : undefined

  const side =
    activeRow && info ? (
      <TermPanel
        key={activeRow.id}
        language={info}
        where={activeRow.context?.bookId && activeRow.context.page ? { bookId: activeRow.context.bookId, page: activeRow.context.page } : undefined}
        target={{ termId: activeRow.id, text: activeRow.text, sentence: 0 }}
        sentenceText={activeRow.context?.sentence ?? ''}
        keysEnabled={checked.size === 0}
        onStatus={onStatus}
        onChanged={onChanged}
        onCreated={onChanged}
        onError={setError}
      />
    ) : (
      <p className="muted">Select a word to see its meaning, its sentence and its status. Use ↑ and ↓ to move, S to hear it.</p>
    )

  const main = (
    <div className="vl">
      <div className="vl-head">
        <div className="vl-title">
          <h1>Vocabulary</h1>
          <span className="muted" aria-live="polite">
            {total === null ? '' : `${total.toLocaleString()} ${total === 1 ? 'word' : 'words'}${filtered ? ' match' : ''}`}
          </span>
          <span className="spacer" />
          <SortMenu filters={filters} onSort={sortBy} />
          <button ref={moreAnchor} className="quiet small icon" aria-label="More" title="More" aria-haspopup="menu" aria-expanded={morePlacement !== null} onClick={() => moreToggle()}>
            ⋯
          </button>
          {morePlacement && (
            <Popover anchor={moreAnchor} placement={morePlacement} onClose={moreClose} label="More" role="menu" className="more-menu">
              <ul>
                <li role="none">
                  <button
                    role="menuitemcheckbox"
                    aria-checked={filters.parentsOnly}
                    onClick={() => {
                      moreClose()
                      change({ parentsOnly: !filters.parentsOnly })
                    }}
                  >
                    {filters.parentsOnly ? '✓ ' : ''}Only words without a parent
                  </button>
                </li>
                <li role="none">
                  <a href={termExportUrl(filters)} download="vocabulary.csv" role="menuitem" onClick={moreClose}>
                    Export as CSV
                  </a>
                </li>
                <li role="none">
                  <button
                    role="menuitem"
                    onClick={() => {
                      moreClose()
                      setMoreOpen(true)
                    }}
                  >
                    Keyboard shortcuts
                  </button>
                </li>
              </ul>
            </Popover>
          )}
        </div>
        <div className="vl-filters">
          <input
            ref={search}
            type="search"
            className="vl-search"
            value={typed}
            placeholder="Search words, translations or parents  ( / )"
            aria-label="Search the vocabulary"
            onChange={(e) => setTyped(e.target.value)}
          />
          {languages.length > 1 && (
            <span className="chips" role="group" aria-label="Language">
              <button className={`chip${filters.language === 0 ? ' on' : ''}`} aria-pressed={filters.language === 0} onClick={() => change({ language: 0 })}>
                All
              </button>
              {languages.map((l) => (
                <button key={l.id} className={`chip${filters.language === l.id ? ' on' : ''}`} aria-pressed={filters.language === l.id} title={l.name} onClick={() => change({ language: filters.language === l.id ? 0 : l.id })}>
                  {languageAbbr(l.name)}
                </button>
              ))}
            </span>
          )}
          <span className="chips" role="group" aria-label="Status">
            {CHIPS.map((c) => (
              <button
                key={c.status}
                className={`chip s${c.status}${filters.statuses.includes(c.status) ? ' on' : ''}`}
                aria-pressed={filters.statuses.includes(c.status)}
                title={`${c.title}${counts[String(c.status)] !== undefined ? ` · ${counts[String(c.status)].toLocaleString()}` : ''}`}
                onClick={() => toggleStatus(c.status)}
              >
                {c.label}
                {counts[String(c.status)] !== undefined && <small>{counts[String(c.status)].toLocaleString()}</small>}
              </button>
            ))}
          </span>
          {tags.length > 0 && (
            <select className="vl-tag" value={filters.tag} aria-label="Tag" onChange={(e) => change({ tag: e.target.value })}>
              <option value="">Any tag</option>
              {tags.map((t) => (
                <option key={t}>{t}</option>
              ))}
            </select>
          )}
          {filtered && (
            <button className="link-button" onClick={clearFilters}>
              Clear filters
            </button>
          )}
        </div>
        {moreOpen && (
          <p className="vl-keys muted">
            <kbd>↑</kbd> <kbd>↓</kbd> move · <kbd>S</kbd> or <kbd>Return</kbd> hear the word · <kbd>Space</kbd> tick it · <kbd>1</kbd>–<kbd>5</kbd>, <kbd>W</kbd>, <kbd>I</kbd> set its status · <kbd>/</kbd> search · <kbd>Esc</kbd> close the panel{' '}
            <button className="link-button" onClick={() => setMoreOpen(false)}>
              Hide
            </button>
          </p>
        )}
      </div>

      {checked.size > 0 && (
        <section className="vl-bulk" aria-label="Change the ticked words">
          <strong>{checked.size} ticked</strong>
          <div className="status-row">
            {STATUS_BUTTONS.map((b) => (
              <button key={b.status} title={`Set status: ${b.title}`} className={`st s${b.status}`} onClick={() => apply({ status: b.status })}>
                {b.label}
              </button>
            ))}
          </div>
          <span className="row-inline">
            <input value={tagInput} placeholder="tag" aria-label="Tag" onChange={(e) => setTagInput(e.target.value)} />
            <button className="secondary small" disabled={!tagInput.trim()} onClick={() => apply({ addTags: [tagInput] })}>
              Add tag
            </button>
            <button className="secondary small" disabled={!tagInput.trim()} onClick={() => apply({ removeTags: [tagInput] })}>
              Remove
            </button>
          </span>
          <span className="row-inline">
            <input value={parentInput} placeholder="parent word" aria-label="Parent word" onChange={(e) => setParentInput(e.target.value)} />
            <button className="secondary small" disabled={!parentInput.trim()} onClick={() => apply({ parent: parentInput })}>
              Set parent
            </button>
            <button className="secondary small" onClick={() => apply({ removeParents: true })}>
              No parent
            </button>
          </span>
          <button className="danger small" onClick={() => apply({ delete: true }, `Delete ${checked.size} ${checked.size === 1 ? 'word' : 'words'}? This cannot be undone.`)}>
            Delete
          </button>
          <button className="quiet small" onClick={() => setChecked(new Set())}>
            Untick
          </button>
        </section>
      )}

      <div className="vl-scroll" ref={scroller}>
        {error && <p className="error">{error}</p>}
        {total === null ? (
          <p className="muted vl-empty">Loading…</p>
        ) : rows.length === 0 ? (
          <div className="vl-empty">
            {filtered || everyStatusOff ? (
              <>
                <p>{everyStatusOff ? 'Every status is switched off.' : 'No word matches.'}</p>
                <button className="secondary" onClick={clearFilters}>
                  Clear filters
                </button>
              </>
            ) : (
              <>
                <p>Words you save while reading appear here.</p>
                <p className="muted">Open a book, click a word and give it a status.</p>
              </>
            )}
          </div>
        ) : (
          <table className="vl-table" aria-label="Vocabulary" aria-rowcount={total}>
            <thead>
              <tr>
                <th className="v-check">
                  <input type="checkbox" aria-label="Tick every word loaded" checked={allChecked} onChange={() => setChecked(allChecked ? new Set() : new Set(rows.map((r) => r.id)))} />
                </th>
                <th className="v-word">Word</th>
                <th className="v-trans">Translation</th>
                <th className="v-context">In context</th>
                {!oneLanguage && <th className="v-lang">Lang</th>}
                <th className="v-status">Status</th>
                <th className="v-added">Added</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr
                  key={r.id}
                  data-row={r.id}
                  className={`${active === r.id ? 'active' : ''}${checked.has(r.id) ? ' checked' : ''}`}
                  aria-selected={active === r.id}
                  onClick={() => setActive(active === r.id ? null : r.id)}
                  onDoubleClick={() => say(r.text, r.languageId)}
                >
                  <td className="v-check" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={checked.has(r.id)}
                      aria-label={`Tick ${r.text}`}
                      onChange={() =>
                        setChecked((c) => {
                          const next = new Set(c)
                          if (!next.delete(r.id)) next.add(r.id)
                          return next
                        })
                      }
                    />
                  </td>
                  <td className="v-word">
                    <span className="v-text">{r.text}</span>
                    {r.parents.length > 0 && <span className="v-parent muted"> ← {r.parents.join(', ')}</span>}
                  </td>
                  <td className="v-trans">{r.translation}</td>
                  <td className="v-context" onClick={(e) => (e.target as HTMLElement).closest('a') && e.stopPropagation()}>
                    {r.context ? (
                      <>
                        <span className="v-sentence" title={r.context.sentence}>
                          {contextParts(r.context.sentence, r.text).map((p, i) => (p.bold ? <b key={i}>{p.text}</b> : p.text))}
                        </span>
                        {r.context.bookId && r.context.page ? (
                          <a className="v-open" href={`#/book/${r.context.bookId}/read/${r.context.page}`} title="Open this page in the book" aria-label="Open this page in the book">
                            ↗
                          </a>
                        ) : null}
                      </>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                  {!oneLanguage && (
                    <td className="v-lang">
                      <span className="lang-chip" title={r.language}>
                        {languageAbbr(r.language)}
                      </span>
                    </td>
                  )}
                  <td className="v-status">
                    <span className={`pill s${r.status}`}>{statusLabel(r.status)}</span>
                  </td>
                  <td className="v-added muted" title={r.created}>
                    {timeAgo(r.created)}
                  </td>
                </tr>
              ))}
              {hasMore && (
                <tr className="v-more">
                  <td colSpan={7} className="muted">
                    {loading ? 'Loading more…' : ''}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )

  return <ReaderLayout left={null} leftOpen={false} focus={false} main={main} side={side} selectionKey={panelId !== null ? `word:${panelId}` : null} onCloseDrawer={() => setActive(null)} />
}
