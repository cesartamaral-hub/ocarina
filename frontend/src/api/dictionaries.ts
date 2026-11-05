import { API, json, send } from './client'

export type DictionaryPack = {
  id: string
  name: string
  language: string // "nl"
  meaning: string // the language of the meanings, "en"
  license: string
  source: string
  kind: 'builtin' | 'wiktionary' | 'stardict' | string
  entries: number
  bytes: number
  on: boolean
  removable: boolean
}

export type DownloadablePack = { id: string; type: 'wikdict' | 'wiktionary'; name: string; language: string; languageName: string; meaning: string; description: string; bytes: number; download: number; installed: boolean; job: string | null }

export type DictionaryList = { packs: DictionaryPack[]; available: DownloadablePack[]; languages: { code: string; name: string }[] }

export const getDictionaries = () => fetch(`${API}/dictionaries`).then((r) => json<DictionaryList>(r))

export const chooseDictionaries = (choice: { order?: string[]; off?: string[] }) => send<{ packs: DictionaryPack[] }>('PUT', `${API}/dictionaries/choice`, choice)

export const deleteDictionary = (id: string) => fetch(`${API}/dictionaries/${id}`, { method: 'DELETE' }).then((r) => json<{ deleted: string }>(r))

export const downloadDictionary = (id: string) => fetch(`${API}/dictionaries/${id}/download`, { method: 'POST' }).then((r) => json<import('./tts').Job>(r))

export const importDictionary = (files: File[], language: string, name: string, meaning = 'en') => {
  const form = new FormData()
  for (const f of files) form.append('files', f)
  form.append('language', language)
  if (name.trim()) form.append('name', name.trim())
  form.append('meaning', meaning)
  return fetch(`${API}/dictionaries/import`, { method: 'POST', body: form }).then((r) => json<import('./tts').Job>(r))
}
