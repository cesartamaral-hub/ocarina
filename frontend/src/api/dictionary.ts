import { API, json } from './client'

export type DefinitionEntry = { partOfSpeech: string; definitions: { text: string; examples: string[] }[] }

export type Definition = {
  found: boolean
  word?: string
  entries?: DefinitionEntry[]
  lemmas?: { word: string; entries: DefinitionEntry[] }[] // base forms that inflected-form definitions point to
  url?: string
  cached?: boolean
  stale?: boolean
  cacheMiss?: boolean
}

// cacheOnly never uses the network: the answer is what was looked up before, or { cacheMiss: true }.
export const getDefinition = (languageId: number, text: string, cacheOnly = false) =>
  fetch(`${API}/dictionary/define?languageId=${languageId}&text=${encodeURIComponent(text)}${cacheOnly ? '&cacheOnly=true' : ''}`).then((r) =>
    json<Definition>(r),
  )
