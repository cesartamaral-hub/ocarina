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
  sentences: Sentence[]
}

export type Model = {
  id: string
  name: string
  description: string
  license: string
  languages: string[]
  installed: boolean
  sizeBytes: number
  downloadJob: string | null
  benchmark?: { secondsPerSecondOfAudio: number; machine: string }
}

export type Job = {
  id: string
  state: 'running' | 'done' | 'error'
  done: number
  total: number
  error?: string
}

const API = '/ocarina/api'

async function json<T>(res: Response): Promise<T> {
  const body = await res.json()
  if (!res.ok) throw Object.assign(new Error(body.error ?? res.statusText), body)
  return body as T
}

export const getBooks = () => fetch(`${API}/books`).then((r) => json<Book[]>(r))

export const getSentences = (id: number) =>
  fetch(`${API}/books/${id}/sentences`).then((r) => json<BookSentences>(r))

export const startAudio = (id: number, opts: { replace?: boolean; pause?: number }) =>
  fetch(`${API}/books/${id}/audio`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(opts),
  }).then((r) => json<Job>(r))

export const getJob = (id: string) => fetch(`${API}/jobs/${id}`).then((r) => json<Job>(r))

export const getModels = () => fetch(`${API}/tts/models`).then((r) => json<Model[]>(r))

export const downloadModel = (id: string) =>
  fetch(`${API}/tts/models/${id}/download`, { method: 'POST' }).then((r) => json<Job>(r))

export const deleteModel = (id: string) =>
  fetch(`${API}/tts/models/${id}`, { method: 'DELETE' }).then((r) => json<{ ok: boolean }>(r))
