import { API, json, send } from './client'

export type Term = {
  id: number | null
  languageId: number
  text: string
  displayText: string
  translation: string
  romanization: string
  status: number
  tags: string[]
  parents: string[]
  syncStatus: boolean
  image: string | null
  components: { id: number; text: string; translation: string; status: number }[]
}

export type Popup = {
  id: number
  text: string
  status: number
  translation: string
  romanization: string
  tags: string[]
  parents: { text: string; translation: string }[]
  image: string | null
}

export type ReferenceSentence = { bookId: number; page: number; title: string; sentence: { text: string; bold: boolean }[] }

export type References = {
  term: ReferenceSentence[]
  children: { term: string; references: ReferenceSentence[] }[]
  parents: { term: string; references: ReferenceSentence[] }[]
}

export const getTerm = (id: number) => fetch(`${API}/terms/${id}`).then((r) => json<Term>(r))

export const saveTerm = (term: Partial<Term> & { status: number }) =>
  send<Term>('POST', `${API}/terms`, term)

export const setTermStatus = (id: number, status: number) =>
  send<{ id: number; status: number }>('PATCH', `${API}/terms/${id}/status`, { status })

export const lookupTerm = (languageId: number, text: string) =>
  fetch(`${API}/terms/lookup?languageId=${languageId}&text=${encodeURIComponent(text)}`).then((r) => json<Term>(r))

export const getPopup = (id: number) => fetch(`${API}/terms/${id}/popup`).then((r) => json<Popup>(r))

export const getReferences = (id: number) =>
  fetch(`${API}/terms/${id}/references`).then((r) => json<References>(r))

export const bulkStatus = (termIds: number[], status: number) =>
  send<{ status: number; count: number }>('POST', `${API}/terms/bulk-status`, { termIds, status })

export const uploadImage = (id: number, file: File) => {
  const form = new FormData()
  form.append('file', file)
  return fetch(`${API}/terms/${id}/image`, { method: 'POST', body: form }).then((r) => json<{ image: string }>(r))
}

export const deleteImage = (id: number) =>
  fetch(`${API}/terms/${id}/image`, { method: 'DELETE' }).then((r) => json<{ image: null }>(r))
