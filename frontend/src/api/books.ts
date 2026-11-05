import { API, json, send } from './client'
import type { Job, SyncStart } from './tts'

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
  video?: { videoId: string } // the YouTube video the book was made from
  currentPage: number
  sentences: Sentence[]
}

export const getBook = (id: number) => fetch(`${API}/books/${id}`).then((r) => json<Book>(r))

export const getBooks = (archived = false) => fetch(`${API}/books?archived=${archived}`).then((r) => json<Book[]>(r))

export const changeBook = (id: number, change: Partial<Pick<Book, 'title' | 'sourceUri' | 'tags' | 'archived'>>) =>
  send<Book>('PATCH', `${API}/books/${id}`, change)

export const deleteBook = (id: number) => fetch(`${API}/books/${id}`, { method: 'DELETE' }).then((r) => json<{ deleted: number }>(r))

export const getSentences = (id: number) =>
  fetch(`${API}/books/${id}/sentences`).then((r) => json<BookSentences>(r))

export type Language = { id: number; name: string; books?: number; terms?: number }

export type Extracted = {
  title: string
  text: string
  sourceUri: string
  note: string | null
  audioToken?: string | null
  videoId?: string | null // a YouTube video: its id, and where its words are said (see ocarina/video.py)
  anchors?: [number, number][] | null
}

export const getLanguages = () => fetch(`${API}/languages`).then((r) => json<Language[]>(r))

export const extractFromFile = (file: File) => {
  const form = new FormData()
  form.append('file', file)
  return fetch(`${API}/books/extract`, { method: 'POST', body: form }).then((r) => json<Extracted>(r))
}

// A web page and a video with captions answer at once; a video that has to be transcribed answers with a job to wait for.
export const extractFromUrl = (url: string, options: { languageId?: number; keepAudio?: boolean } = {}) =>
  send<Extracted | Job>('POST', `${API}/books/extract`, { url, ...options })

export type NewBook = {
  title: string
  languageId: number
  text: string
  sourceUri: string
  audio: File | null
  importAudio?: string | null // the sound of an imported video (see Extracted.audioToken)
  video?: { videoId: string; anchors: [number, number][] } | null // the video to play in the reader
  translate?: { provider: string; model: string | null } | null // translate the whole text once it is saved, this way
}

export type BookSaved = {
  id: number
  sync?: SyncStart
  translation?: { state: 'started'; job: Job } | { state: 'failed'; error: string }
}

export const createBook = (b: NewBook) => {
  const form = new FormData()
  form.append('title', b.title)
  form.append('languageId', String(b.languageId))
  form.append('text', b.text)
  form.append('sourceUri', b.sourceUri)
  if (b.audio) form.append('audio', b.audio)
  else if (b.importAudio) form.append('importAudio', b.importAudio)
  if (b.translate) {
    form.append('translate', '1')
    form.append('translateProvider', b.translate.provider)
    if (b.translate.model) form.append('translateModel', b.translate.model)
  }
  if (b.video) {
    form.append('videoId', b.video.videoId)
    form.append('videoAnchors', JSON.stringify(b.video.anchors))
  }
  return fetch(`${API}/books`, { method: 'POST', body: form }).then((r) => json<BookSaved>(r))
}
