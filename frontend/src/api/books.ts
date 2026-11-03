import { API, json } from './client'

export type Book = {
  id: number
  title: string
  language: string
  hasAudio: boolean
  ocarinaAudio: boolean
  pages: number
}

export type Sentence = { page: number; text: string; start?: number }

export type BookSentences = {
  id: number
  title: string
  language: string
  hasAudio: boolean
  hasTimings: boolean
  currentPage: number
  sentences: Sentence[]
}

export const getBooks = () => fetch(`${API}/books`).then((r) => json<Book[]>(r))

export const getSentences = (id: number) =>
  fetch(`${API}/books/${id}/sentences`).then((r) => json<BookSentences>(r))
