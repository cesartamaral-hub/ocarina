import { API, json, send } from './client'

export type ListRow = {
  id: number
  text: string
  parents: string[]
  translation: string
  language: string
  languageId: number
  tags: string[]
  status: number
  created: string
  context: { sentence: string; bookId: number | null; page: number | null; found: boolean } | null // where it was saved from
}

export type TermFilters = {
  language: number
  q: string
  statuses: number[] // the status chips that are on
  parentsOnly: boolean
  tag: string
  sort: string
  order: 'asc' | 'desc'
  page: number
  pageSize: number
}

export type TermPage = { total: number; page: number; pageSize: number; rows: ListRow[]; counts?: Record<string, number> }

const query = (f: TermFilters) => {
  const p = new URLSearchParams({
    language: String(f.language),
    q: f.q,
    statuses: f.statuses.join(','),
    parentsOnly: String(f.parentsOnly),
    tag: f.tag,
    sort: f.sort,
    order: f.order,
    page: String(f.page),
    pageSize: String(f.pageSize),
    counts: 'true',
  })
  return p.toString()
}

export const getTermList = (f: TermFilters) => fetch(`${API}/term-list?${query(f)}`).then((r) => json<TermPage>(r))

export const termExportUrl = (f: TermFilters) => `${API}/term-list/export?${query(f)}`

export const getTags = () => fetch(`${API}/tags`).then((r) => json<string[]>(r))

export type BulkChange = {
  ids: number[]
  status?: number
  addTags?: string[]
  removeTags?: string[]
  parent?: string
  removeParents?: boolean
  delete?: boolean
}

export const bulkChange = (change: BulkChange) => send<{ updated?: number; deleted?: number }>('POST', `${API}/terms/bulk`, change)
