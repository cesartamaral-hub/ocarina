import { API, json, send } from './client'

export type Dictionary = { url: string; dicttype: string }

export type Item = {
  text: string
  display: string
  isWord: boolean
  termId: number | null
  status: number
  sentence: number
  index: number
}

export type ReaderPage = {
  bookId: number
  title: string
  language: {
    id: number
    name: string
    rightToLeft: boolean
    showRomanization: boolean
    dictionaries: Dictionary[]
    sentenceDictionaries: Dictionary[]
  }
  page: number
  pageCount: number
  paragraphs: Item[][][]
}

export const getPage = (bookId: number, page: number) =>
  fetch(`${API}/books/${bookId}/pages/${page}`).then((r) => json<ReaderPage>(r))

export const finishPage = (bookId: number, page: number, restAsKnown: boolean) =>
  send<{ ok: boolean }>('POST', `${API}/books/${bookId}/pages/${page}/finish`, { restAsKnown })

export const getPageText = (bookId: number, page: number) =>
  fetch(`${API}/books/${bookId}/pages/${page}/text`).then((r) => json<{ text: string }>(r))

export const putPageText = (bookId: number, page: number, text: string) =>
  send<{ ok: boolean }>('PUT', `${API}/books/${bookId}/pages/${page}/text`, { text })

export const openExternal = (url: string) =>
  send<{ ok: boolean }>('POST', `${API}/open-external`, { url })
