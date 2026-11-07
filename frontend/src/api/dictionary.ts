import { API, json } from './client'

export type DefinitionEntry = {
  partOfSpeech: string
  definitions: { text: string; examples: string[] }[]
}

export type DictionarySource = {
  id: string
  name: string
  license: string
  offline: boolean
}

export type DefinitionOther = {
  source: DictionarySource
  entries: DefinitionEntry[]
  lemmas: { word: string; entries: DefinitionEntry[] }[]
  url?: string
}

export type Definition = {
  found: boolean
  word?: string
  entries?: DefinitionEntry[]
  lemmas?: { word: string; entries: DefinitionEntry[] }[] // base forms that inflected-form definitions point to
  url?: string
  cached?: boolean
  stale?: boolean
  cacheMiss?: boolean
  source?: DictionarySource // the dictionary that answered
  others?: DefinitionOther[] // the other dictionaries that know the word
}

// The dictionaries on this Mac answer first. cacheOnly never uses the network: the answer is what was looked up before, or { cacheMiss: true }.
// online also asks Wiktionary over the internet, for a second opinion.
export const getDefinition = (languageId: number, text: string, cacheOnly = false, online = false) =>
  fetch(
    `${API}/dictionary/define?languageId=${languageId}&text=${encodeURIComponent(text)}${cacheOnly ? '&cacheOnly=true' : ''}${online ? '&online=true' : ''}`,
  ).then((r) => json<Definition>(r))

export type SelectionPart = {
  text: string
  words: number
  source: DictionarySource
  entries: DefinitionEntry[]
}

// What the dictionaries on this Mac know inside a selection of several words (runs of two or more words, then single words).
export const getParts = (languageId: number, text: string) =>
  fetch(`${API}/dictionary/parts?languageId=${languageId}&text=${encodeURIComponent(text)}`).then((r) =>
    json<{ parts: SelectionPart[] }>(r),
  )
