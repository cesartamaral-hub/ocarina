import { API, json } from './client'

export type Readiness = {
  offline: boolean
  languages: { code: string; name: string; dictionary: { ok: boolean; names: string[] }; translation: { ok: boolean; names: string[] }; voice: { ok: boolean; names: string[] } }[]
  audioSync: { ok: boolean; name: string }
}

export const getOffline = () => fetch(`${API}/offline`).then((r) => json<Readiness>(r))
