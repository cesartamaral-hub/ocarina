import { API, json, send } from './client'

export type Book = {
  id: number
  title: string
  language: string
  hasAudio: boolean
  ocarinaAudio: boolean
  pages: number
  currentPage: number
  sourceUri: string
  tags: string[]
  archived: boolean
  stats: BookStats | null // null until the book's word index is built
  indexing: boolean
  lastRead: string | null
}

export type BookStats = {
  words: number
  unique: number
  known: number
  learning: number
  ignored: number
  new: number
  newUnique: number
  knownPercent: number
  minutes: number
}

export type Sentence = { page: number; text: string; start?: number }

export type BookSentences = {
  id: number
  title: string
  language: string
  hasAudio: boolean
  hasTimings: boolean
  audioModel?: string
  currentPage: number
  sentences: Sentence[]
}

export const getBooks = (archived = false) => fetch(`${API}/books?archived=${archived}`).then((r) => json<Book[]>(r))

export const changeBook = (id: number, change: Partial<Pick<Book, 'title' | 'sourceUri' | 'tags' | 'archived'>>) =>
  send<Book>('PATCH', `${API}/books/${id}`, change)

export const deleteBook = (id: number) => fetch(`${API}/books/${id}`, { method: 'DELETE' }).then((r) => json<{ deleted: number }>(r))

export const getSentences = (id: number) =>
  fetch(`${API}/books/${id}/sentences`).then((r) => json<BookSentences>(r))

export type Language = { id: number; name: string; books?: number; terms?: number }

export type Extracted = { title: string; text: string; sourceUri: string; note: string | null }

export const getLanguages = () => fetch(`${API}/languages`).then((r) => json<Language[]>(r))

export const extractFromFile = (file: File) => {
  const form = new FormData()
  form.append('file', file)
  return fetch(`${API}/books/extract`, { method: 'POST', body: form }).then((r) => json<Extracted>(r))
}

export const extractFromUrl = (url: string) => send<Extracted>('POST', `${API}/books/extract`, { url })

export type NewBook = {
  title: string
  languageId: number
  text: string
  sourceUri: string
  audio: File | null
}

export const createBook = (b: NewBook) => {
  const form = new FormData()
  form.append('title', b.title)
  form.append('languageId', String(b.languageId))
  form.append('text', b.text)
  form.append('sourceUri', b.sourceUri)
  if (b.audio) form.append('audio', b.audio)
  return fetch(`${API}/books`, { method: 'POST', body: form }).then((r) => json<{ id: number }>(r))
}
