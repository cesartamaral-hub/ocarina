import { API, json, send } from './client'
import type { Job } from './tts'

export type TranslatedSentence = { page: number; index: number; translation: string | null; stale: boolean }

// A book's translated version, sentence by sentence, and who makes it.
export type BookTranslation = {
  target: string
  targetName: string
  provider: string
  providerName: string
  dailyLimit: number | null // characters a day the service allows, when it has a limit
  sentences: TranslatedSentence[]
  total: number
  done: number
  stale: number // translated, but the sentence was edited since
  remainingChars: number
  remainingByPage: Record<string, number>
  running: boolean
}

export const getBookTranslation = (bookId: number) => fetch(`${API}/books/${bookId}/translation`).then((r) => json<BookTranslation>(r))

export const startBookTranslation = (bookId: number, scope: 'page' | 'book', page?: number) =>
  send<Job>('POST', `${API}/books/${bookId}/translation`, { scope, page })

export const correctTranslation = (bookId: number, page: number, index: number, text: string) =>
  send<{ translation: string }>('PUT', `${API}/books/${bookId}/translation/${page}/${index}`, { text })

export const removeBookTranslation = (bookId: number) => fetch(`${API}/books/${bookId}/translation`, { method: 'DELETE' }).then((r) => json<{ ok: boolean }>(r))
