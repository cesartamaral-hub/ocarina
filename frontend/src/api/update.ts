import { API, json, send } from './client'

export type UpdateStatus = {
  current: string
  enabled: boolean
  offline: boolean
  canInstall: boolean
  latest: { version: string; notes: string; url: string; size: number; newer: boolean } | null
  show: boolean
  skipped: string | null
  download: { state: 'idle' | 'running' | 'done' | 'error'; done: number; total: number; error: string; version: string }
  error?: string
}

export const getUpdate = (force = false) => fetch(`${API}/update${force ? '?force=1' : ''}`).then((r) => json<UpdateStatus>(r))
export const setUpdateCheck = (check: boolean) => send<{ check: boolean }>('PUT', `${API}/update/settings`, { check })
export const skipUpdate = (version: string) => send<{ skipped: string }>('POST', `${API}/update/skip`, { version })
export const unskipUpdate = () => send<{ skipped: null }>('POST', `${API}/update/unskip`, {})
export const updateLater = () => send<{ ok: boolean }>('POST', `${API}/update/later`, {})
export const downloadUpdate = () => send<UpdateStatus['download']>('POST', `${API}/update/download`, {})
export const installUpdate = () => send<{ restarting: boolean }>('POST', `${API}/update/install`, {})
