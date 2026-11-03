import { API, json, send } from './client'

export type DictionarySetting = { useFor: 'terms' | 'sentences'; dictType: 'embeddedhtml' | 'popuphtml'; url: string; active: boolean }

export type LanguageSettings = {
  id: number | null
  name: string
  parserType: string
  showRomanization: boolean
  rightToLeft: boolean
  characterSubstitutions: string
  regexpSplitSentences: string
  exceptionsSplitSentences: string
  wordCharacters: string
  dictionaries: DictionarySetting[]
}

export type LanguageTemplate = { language: LanguageSettings; predefined: string[] }

export const getLanguageSettings = (id: number) => fetch(`${API}/languages/${id}`).then((r) => json<LanguageSettings>(r))

export const getLanguageTemplate = (name?: string) =>
  fetch(`${API}/languages/template${name ? `?name=${encodeURIComponent(name)}` : ''}`).then((r) => json<LanguageTemplate>(r))

export const getParsers = () => fetch(`${API}/languages/parsers`).then((r) => json<{ type: string; name: string }[]>(r))

export const saveLanguage = (l: LanguageSettings) =>
  l.id === null ? send<LanguageSettings>('POST', `${API}/languages`, l) : send<LanguageSettings>('PUT', `${API}/languages/${l.id}`, l)

export const deleteLanguage = (id: number, force: boolean) =>
  fetch(`${API}/languages/${id}${force ? '?force=true' : ''}`, { method: 'DELETE' }).then((r) =>
    json<{ deleted: number; books: number; terms: number }>(r),
  )
