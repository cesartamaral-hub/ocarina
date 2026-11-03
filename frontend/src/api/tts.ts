import { API, json } from './client'

export type Job = {
  id: string
  kind: 'audio' | 'download'
  state: 'queued' | 'running' | 'done' | 'error' | 'cancelled'
  done: number
  total: number
  queuePosition?: number
  book_id?: number
  model_id?: string
  error?: string
}

export const isActive = (job: Job | null) => job?.state === 'queued' || job?.state === 'running'

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

export const getModels = () => fetch(`${API}/tts/models`).then((r) => json<Model[]>(r))

export const downloadModel = (id: string) =>
  fetch(`${API}/tts/models/${id}/download`, { method: 'POST' }).then((r) => json<Job>(r))

export const deleteModel = (id: string) =>
  fetch(`${API}/tts/models/${id}`, { method: 'DELETE' }).then((r) => json<{ ok: boolean }>(r))

export const importModel = (id: string, folder: string) =>
  fetch(`${API}/tts/models/${id}/import`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ folder }),
  }).then((r) => json<Job>(r))

// Native folder dialog; only exists inside the desktop app (the dev browser has none).
type Bridge = { pick_folder: () => Promise<string | null> }
export const canPickFolder = () => Boolean((window as { pywebview?: { api?: Bridge } }).pywebview?.api)
export const pickFolder = () =>
  (window as unknown as { pywebview: { api: Bridge } }).pywebview.api.pick_folder()

export const getActiveJobs = () => fetch(`${API}/jobs`).then((r) => json<Job[]>(r))

export const cancelJob = (id: string) => fetch(`${API}/jobs/${id}/cancel`, { method: 'POST' }).then((r) => json<Job>(r))

export const getJob = (id: string) => fetch(`${API}/jobs/${id}`).then((r) => json<Job>(r))

export const startAudio = (id: number, opts: { replace?: boolean; pause?: number }) =>
  fetch(`${API}/books/${id}/audio`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(opts),
  }).then((r) => json<Job>(r))
