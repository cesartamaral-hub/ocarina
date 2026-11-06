import { API, json, send } from './client'

export type Job = {
  id: string
  kind: 'audio' | 'download' | 'preview' | 'check' | 'sync' | 'translate' | 'import' | 'dictionary'
  state: 'queued' | 'running' | 'done' | 'error' | 'cancelled'
  done: number
  total: number
  queuePosition?: number
  title?: string
  phase?: string // 'testing' while a model is being tried after its download
  detail?: string // the original error text, when the error above is a plain-language explanation
  book_id?: number
  model_id?: string
  pack_id?: string // dictionary jobs: the dictionary being downloaded
  preview?: string
  error?: string
  message?: string // import jobs: what is happening now
  result?: { title: string; text: string; sourceUri: string; note: string | null; audioToken: string | null } // import jobs, when done
  suspect?: number // sync jobs: sentences that could not be placed with confidence
}

export const isActive = (job: Job | null) => job?.state === 'queued' || job?.state === 'running'

export type ModelCheck = {
  ok: boolean
  error?: string
  detail?: string
  secondsPerSecondOfAudio?: number | null
  secondsPerSentence?: number
  loadSeconds?: number
  at: number
}

export type Model = {
  id: string
  name: string
  description: string
  license: string
  languages: string[]
  installed: boolean
  kind?: 'speech' | 'text' | 'aligner' | 'transcriber'
  custom?: boolean
  check?: ModelCheck | null
  sizeBytes: number
  downloadJob: string | null
  downloadError?: string | null // why the last download failed (until the model is installed or a new download starts)
  grades?: Record<string, string> // how well it does in a language, A to D (the catalog's own estimate)
  speed?: number // 1 to 4, before it has been tried here
  badge?: string
  starter?: boolean // part of the set Welcome ticks for you; the other recommended models are only for one feature
  benchmark?: { secondsPerSecondOfAudio?: number; secondsPerSentence?: number; machine: string }
}

export const getModels = () => fetch(`${API}/tts/models`).then((r) => json<Model[]>(r))

export type DiskSpace = { freeBytes: number; marginBytes: number; queuedBytes: number }

export const getDiskSpace = () => fetch(`${API}/tts/models/space`).then((r) => json<DiskSpace>(r))

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

// A recording added to a material is synced with its text at once: the job, or why there is none.
export type SyncStart = { state: 'started'; job: Job } | { state: 'model_missing'; error: string; model?: string } | { state: 'busy'; error: string } | null

export const uploadAudio = (bookId: number, file: File) => {
  const form = new FormData()
  form.append('audio', file)
  return fetch(`${API}/books/${bookId}/audio/upload`, { method: 'POST', body: form }).then((r) =>
    json<{ audio_filename: string; versionId: number; sync?: SyncStart }>(r),
  )
}

export const getJob = (id: string) => fetch(`${API}/jobs/${id}`).then((r) => json<Job>(r))

export type AudioOptions = {
  language: string
  defaultModel: string
  defaultVoice: string
  models: { id: string; name: string; installed: boolean; custom: boolean; problem?: string | null }[]
  voices: { id: string; name: string; builtin: boolean }[]
}

export const getAudioOptions = (bookId: number) => fetch(`${API}/books/${bookId}/audio/options`).then((r) => json<AudioOptions>(r))

export type AudioVersion = {
  id: number
  label: string
  kind: 'own' | 'generated'
  model: string | null
  modelName: string | null
  voice: string | null
  pause: number | null
  created: string
  selected: boolean
  hasTimings: boolean
  synced: boolean // your own recording, synced with the text
  missing: boolean
}

export const getAudioVersions = (bookId: number) => fetch(`${API}/books/${bookId}/audio/versions`).then((r) => json<AudioVersion[]>(r))

export const selectAudioVersion = (bookId: number, id: number) =>
  fetch(`${API}/books/${bookId}/audio/versions/${id}/select`, { method: 'PUT' }).then((r) => json<AudioVersion[]>(r))

export const renameAudioVersion = (bookId: number, id: number, label: string) =>
  send<AudioVersion[]>('PATCH', `${API}/books/${bookId}/audio/versions/${id}`, { label })

export const deleteAudioVersion = (bookId: number, id: number) =>
  fetch(`${API}/books/${bookId}/audio/versions/${id}`, { method: 'DELETE' }).then((r) =>
    json<{ removed: AudioVersion; versions: AudioVersion[] }>(r),
  )

export const startAudio = (id: number, opts: { pause?: number; model?: string; voice?: string }) =>
  fetch(`${API}/books/${id}/audio`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(opts),
  }).then((r) => json<Job>(r))

export const syncAudioVersion = (bookId: number, versionId: number) =>
  fetch(`${API}/books/${bookId}/audio/versions/${versionId}/sync`, { method: 'POST' }).then((r) => json<Job>(r))

export type Voice = { id: string; name: string; builtin: boolean; seconds: number; transcript: string }

export const getVoices = () => fetch(`${API}/tts/voices`).then((r) => json<Voice[]>(r))

export const addVoice = (clip: File, name: string, transcript: string) => {
  const form = new FormData()
  form.append('clip', clip)
  if (name.trim()) form.append('name', name.trim())
  if (transcript.trim()) form.append('transcript', transcript.trim())
  return fetch(`${API}/tts/voices`, { method: 'POST', body: form }).then((r) => json<Voice>(r))
}

export const deleteVoice = (id: string) =>
  fetch(`${API}/tts/voices/${encodeURIComponent(id)}`, { method: 'DELETE' }).then((r) => json<{ deleted: string }>(r))

export const previewVoice = (voice: string, language: string) =>
  send<Job>('POST', `${API}/tts/voices/preview`, { voice, language })

export const previewUrl = (name: string) => `${API}/tts/previews/${name}`

export type HubLookup = {
  repo: string
  revision: string
  license: string
  files: number
  totalBytes: number
  modelType: string | null
  support: { known: boolean | null; module: string | null; problem: string | null; text?: { known: boolean | null } }
  memoryGb: number
  converted: boolean
  notes: string[]
}

export const getEngines = () =>
  fetch(`${API}/tts/engines`).then((r) => json<{ engines: { id: string; name: string }[]; languages: string[] }>(r))

export const checkModel = (id: string) => send<Job>('POST', `${API}/tts/models/${id}/check`, {})

export const lookupModel = (repo: string) => send<HubLookup>('POST', `${API}/tts/models/lookup`, { repo })

export const addCustomModel = (m: { repo: string; engine: string; languages: string[]; name: string }) =>
  send<Model>('POST', `${API}/tts/models/custom`, m)

export const removeModelEntry = (id: string) =>
  fetch(`${API}/tts/models/${id}/entry`, { method: 'DELETE' }).then((r) => json<{ removed: string }>(r))
