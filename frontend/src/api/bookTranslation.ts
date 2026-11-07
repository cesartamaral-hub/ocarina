import { API, json, send } from './client'
import type { Job } from './tts'

// A way to translate: a model on this Mac, MyMemory or DeepL.
export type TranslationMethod = {
  provider: string
  model: string | null
  name: string
  available: boolean
  reason: string | null
  isDefault: boolean
  secondsPerSentence: number // how long one sentence takes this way (an estimate)
}

export type TranslatedSentence = {
  page: number
  index: number
  translation: string | null
  stale: boolean
}

// A book's translated version, sentence by sentence, and who makes it.
export type BookTranslation = {
  target: string
  targetName: string
  provider: string
  providerName: string
  methods: TranslationMethod[]
  dailyLimit: number | null // characters a day the service allows, when it has a limit
  sentences: TranslatedSentence[]
  total: number
  done: number
  stale: number // translated, but the sentence was edited since
  remainingChars: number
  remainingByPage: Record<string, number>
  running: boolean
  offline?: boolean // Work offline is on
}

export const getBookTranslation = (bookId: number) =>
  fetch(`${API}/books/${bookId}/translation`).then((r) => json<BookTranslation>(r))

// method: another way than the default, for this run only.
export const startBookTranslation = (
  bookId: number,
  scope: 'page' | 'book',
  page?: number,
  method?: { provider: string; model: string | null },
  redo = false,
) =>
  send<Job>('POST', `${API}/books/${bookId}/translation`, {
    scope,
    page,
    ...(redo ? { redo } : {}),
    ...(method ? { provider: method.provider, model: method.model } : {}),
  })

export const correctTranslation = (bookId: number, page: number, index: number, text: string) =>
  send<{ translation: string }>('PUT', `${API}/books/${bookId}/translation/${page}/${index}`, { text })

export const removeBookTranslation = (bookId: number) =>
  fetch(`${API}/books/${bookId}/translation`, { method: 'DELETE' }).then((r) => json<{ ok: boolean }>(r))
