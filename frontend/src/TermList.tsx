import { Fragment, useEffect, useState } from 'react'
import {
  bulkChange,
  getLanguages,
  getTags,
  getTerm,
  getTermList,
  saveTerm,
  termExportUrl,
  type BulkChange,
  type Language,
  type ListRow,
  type Term,
  type TermFilters,
  type TermPage,
} from './api'
import { STATUS_BUTTONS } from './reader/statuses'

const STATUS_CHOICES = [0, 1, 2, 3, 4, 5, 99]
const DEFAULTS: TermFilters = {
  language: 0,
  q: '',
  statusMin: 0,
  statusMax: 99,
  includeIgnored: false,
  parentsOnly: false,
  tag: '',
  sort: 'text',
  order: 'asc',
  page: 1,
  pageSize: 50,
}
const COLUMNS: [string, string][] = [
  ['text', 'Term'],
  ['parent', 'Parent'],
  ['translation', 'Translation'],
  ['language', 'Language'],
  ['status', 'Status'],
  ['created', 'Added'],
]

const statusLabel = (s: number) => (s === 99 ? '✓' : s === 98 ? '✕' : String(s))

function EditRow({ id, onSaved, onDeleted }: { id: number; onSaved: () => void; onDeleted: () => void }) {
  const [term, setTerm] = useState<Term | null>(null)
  const [parents, setParents] = useState('')
  const [tags, setTags] = useState('')
  const [error, setError] = useState('')
  useEffect(() => {
    getTerm(id).then(
      (t) => {
        setTerm(t)
        setParents(t.parents.join(', '))
        setTags(t.tags.join(', '))
      },
      (e) => setError(e.message),
    )
  }, [id])
  if (!term) return <p className={error ? 'error' : 'muted'}>{error || 'Loading…'}</p>
  const list = (v: string) => v.split(',').map((s) => s.trim()).filter(Boolean)
  async function save() {
    try {
      await saveTerm({ ...term!, parents: list(parents), tags: list(tags) })
      onSaved()
    } catch (e) {
      setError((e as Error).message)
    }
  }
  return (
    <div className="form term-edit">
      <label>
        Translation
        <textarea rows={2} value={term.translation} onChange={(e) => setTerm({ ...term, translation: e.target.value })} />
      </label>
      <label>
        Pronunciation
        <input value={term.romanization} onChange={(e) => setTerm({ ...term, romanization: e.target.value })} />
      </label>
      <label>
        Parents (comma separated)
        <input value={parents} onChange={(e) => setParents(e.target.value)} />
      </label>
      <label>
        Tags (comma separated)
        <input value={tags} onChange={(e) => setTags(e.target.value)} />
      </label>
      <div className="status-row">
        {STATUS_BUTTONS.map((b) => (
          <button
            key={b.status}
            title={b.title}
            className={`st s${b.status}${term.status === b.status ? ' on' : ''}`}
            onClick={() => setTerm({ ...term, status: b.status })}
          >
            {b.label}
          </button>
        ))}
      </div>
      {error && <p className="error">{error}</p>}
      <div className="actions">
        <button onClick={save}>Save</button>
        <button className="secondary" onClick={onDeleted}>
          Delete term
        </button>
      </div>
    </div>
  )
}

export function TermList() {
  const [filters, setFilters] = useState<TermFilters>(DEFAULTS)
  const [typed, setTyped] = useState('')
  const [languages, setLanguages] = useState<Language[]>([])
  const [tags, setTags] = useState<string[]>([])
  const [data, setData] = useState<TermPage | null>(null)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [open, setOpen] = useState<number | null>(null)
  const [error, setError] = useState('')
  const [tick, setTick] = useState(0)
  const [tagInput, setTagInput] = useState('')
  const [parentInput, setParentInput] = useState('')

  useEffect(() => {
    getLanguages().then(setLanguages, () => undefined)
    getTags().then(setTags, () => undefined)
  }, [tick])

  // The search box waits for a pause in typing before it asks the server.
  useEffect(() => {
    const timer = setTimeout(() => setFilters((f) => (f.q === typed ? f : { ...f, q: typed, page: 1 })), 300)
    return () => clearTimeout(timer)
  }, [typed])

  const key = JSON.stringify(filters)
  useEffect(() => {
    const stale = new AbortController() // answers that arrive after the filters changed are ignored
    getTermList(JSON.parse(key) as TermFilters).then(
      (d) => !stale.signal.aborted && (setData(d), setError('')),
      (e) => !stale.signal.aborted && setError(e.message),
    )
    return () => stale.abort()
  }, [key, tick])

  function change(patch: Partial<TermFilters>) {
    setFilters((f) => ({ ...f, page: 1, ...patch }))
    setSelected(new Set())
    setOpen(null)
  }
  const reload = () => setTick((t) => t + 1)

  function sortBy(column: string) {
    change({ sort: column, order: filters.sort === column && filters.order === 'asc' ? 'desc' : 'asc' })
  }

  async function apply(change_: Omit<BulkChange, 'ids'>, confirmText?: string) {
    if (confirmText && !window.confirm(confirmText)) return
    setError('')
    try {
      await bulkChange({ ids: [...selected], ...change_ })
      setSelected(new Set())
      setOpen(null)
      reload()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  const rows = data?.rows ?? []
  const pages = data ? Math.max(1, Math.ceil(data.total / data.pageSize)) : 1
  const allOnPage = rows.length > 0 && rows.every((r) => selected.has(r.id))
  const toggle = (r: ListRow) =>
    setSelected((s) => {
      const next = new Set(s)
      if (!next.delete(r.id)) next.add(r.id)
      return next
    })

  return (
    <>
      <h1>Terms</h1>
      <section className="panel static filters">
        <div className="controls">
          <label>
            Search
            <input value={typed} placeholder="term, translation or parent" onChange={(e) => setTyped(e.target.value)} />
          </label>
          <label>
            Language
            <select value={filters.language} onChange={(e) => change({ language: Number(e.target.value) })}>
              <option value={0}>All</option>
              {languages.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Status from
            <select value={filters.statusMin} onChange={(e) => change({ statusMin: Number(e.target.value) })}>
              {STATUS_CHOICES.map((s) => (
                <option key={s} value={s}>
                  {s === 0 ? 'any' : statusLabel(s)}
                </option>
              ))}
            </select>
          </label>
          <label>
            to
            <select value={filters.statusMax} onChange={(e) => change({ statusMax: Number(e.target.value) })}>
              {STATUS_CHOICES.filter((s) => s > 0).map((s) => (
                <option key={s} value={s}>
                  {statusLabel(s)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Tag
            <select value={filters.tag} onChange={(e) => change({ tag: e.target.value })}>
              <option value="">any</option>
              {tags.map((t) => (
                <option key={t}>{t}</option>
              ))}
            </select>
          </label>
          <label className="inline">
            <input type="checkbox" checked={filters.includeIgnored} onChange={(e) => change({ includeIgnored: e.target.checked })} />
            Ignored too
          </label>
          <label className="inline">
            <input type="checkbox" checked={filters.parentsOnly} onChange={(e) => change({ parentsOnly: e.target.checked })} />
            Without a parent
          </label>
          <a className="button secondary" href={termExportUrl(filters)} download="terms.csv">
            Export CSV
          </a>
        </div>
      </section>

      {selected.size > 0 && (
        <section className="panel bulk">
          <strong>{selected.size} selected</strong>
          <div className="status-row">
            {STATUS_BUTTONS.map((b) => (
              <button key={b.status} title={`Set status: ${b.title}`} className={`st s${b.status}`} onClick={() => apply({ status: b.status })}>
                {b.label}
              </button>
            ))}
          </div>
          <span className="row-inline">
            <input value={tagInput} placeholder="tag" onChange={(e) => setTagInput(e.target.value)} />
            <button className="secondary" disabled={!tagInput.trim()} onClick={() => apply({ addTags: [tagInput] })}>
              Add tag
            </button>
            <button className="secondary" disabled={!tagInput.trim()} onClick={() => apply({ removeTags: [tagInput] })}>
              Remove tag
            </button>
          </span>
          <span className="row-inline">
            <input value={parentInput} placeholder="parent term" onChange={(e) => setParentInput(e.target.value)} />
            <button className="secondary" disabled={!parentInput.trim()} onClick={() => apply({ parent: parentInput })}>
              Set parent
            </button>
            <button className="secondary" onClick={() => apply({ removeParents: true })}>
              Remove parents
            </button>
          </span>
          <button className="danger" onClick={() => apply({ delete: true }, `Delete ${selected.size} terms? This cannot be undone.`)}>
            Delete
          </button>
        </section>
      )}

      {error && <p className="error">{error}</p>}
      {!data ? (
        <p className="muted">Loading…</p>
      ) : (
        <>
          <p className="muted">
            {data.total} {data.total === 1 ? 'term' : 'terms'}
          </p>
          <table className="terms">
            <thead>
              <tr>
                <th>
                  <input
                    type="checkbox"
                    aria-label="Select all on this page"
                    checked={allOnPage}
                    onChange={() => setSelected(allOnPage ? new Set() : new Set(rows.map((r) => r.id)))}
                  />
                </th>
                {COLUMNS.map(([column, label]) => (
                  <th key={column} onClick={() => sortBy(column)} className="sortable">
                    {label}
                    {filters.sort === column ? (filters.order === 'asc' ? ' ▲' : ' ▼') : ''}
                  </th>
                ))}
                <th>Tags</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <Fragment key={r.id}>
                  <tr className={open === r.id ? 'open' : ''}>
                    <td>
                      <input type="checkbox" checked={selected.has(r.id)} onChange={() => toggle(r)} aria-label={`Select ${r.text}`} />
                    </td>
                    <td className="term-text" onClick={() => setOpen(open === r.id ? null : r.id)}>
                      {r.text}
                    </td>
                    <td>{r.parents.join(', ')}</td>
                    <td>{r.translation}</td>
                    <td>{r.language}</td>
                    <td>
                      <span className={`pill s${r.status}`}>{statusLabel(r.status)}</span>
                    </td>
                    <td className="muted">{r.created?.slice(0, 10)}</td>
                    <td className="muted">{r.tags.join(', ')}</td>
                  </tr>
                  {open === r.id && (
                    <tr>
                      <td colSpan={8}>
                        <EditRow
                          id={r.id}
                          onSaved={() => {
                            setOpen(null)
                            reload()
                          }}
                          onDeleted={async () => {
                            if (!window.confirm(`Delete "${r.text}"?`)) return
                            await bulkChange({ ids: [r.id], delete: true }).catch((e) => setError(e.message))
                            setOpen(null)
                            reload()
                          }}
                        />
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
          <div className="pager">
            <button className="secondary" disabled={filters.page <= 1} onClick={() => change({ page: filters.page - 1 })}>
              ← Previous
            </button>
            <span className="muted">
              Page {filters.page} of {pages}
            </span>
            <button className="secondary" disabled={filters.page >= pages} onClick={() => change({ page: filters.page + 1 })}>
              Next →
            </button>
            <select value={filters.pageSize} onChange={(e) => change({ pageSize: Number(e.target.value) })}>
              {[25, 50, 100, 200].map((n) => (
                <option key={n} value={n}>
                  {n} per page
                </option>
              ))}
            </select>
          </div>
        </>
      )}
    </>
  )
}
