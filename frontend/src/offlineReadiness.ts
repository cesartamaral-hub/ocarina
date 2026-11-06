import type { Readiness } from './api'

export type OfflineNote = { text: string; page: string; href: string } // what will not work offline, and the page to look at

const list = (names: string[]) => (names.length < 2 ? names.join('') : `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`)

// The lines under the Work offline switch: a gentle suggestion for each thing that would not work offline, with the page to check. Nothing is
// said when everything for your languages is on this Mac.
export function offlineSummary(ready: Readiness): { ok: boolean; text: string; notes: OfflineNote[] } {
  const all = ready.languages
  if (all.length === 0) return { ok: true, text: '', notes: [] }
  const lacking = (key: 'dictionary' | 'translation' | 'voice') => all.filter((l) => !l[key].ok).map((l) => l.name)
  const notes: OfflineNote[] = []
  const translation = lacking('translation')
  if (translation.length === all.length) notes.push({ text: "You have no local translation model downloaded, so translation won't work offline.", page: 'Models', href: '#/settings/models' })
  else if (translation.length > 0)
    notes.push({ text: `There is no local translation model for ${list(translation)}, so translating ${translation.length === 1 ? 'it' : 'them'} won't work offline.`, page: 'Models', href: '#/settings/models' })
  const dictionary = lacking('dictionary')
  if (dictionary.length > 0) notes.push({ text: `There is no dictionary for ${list(dictionary)} on this Mac, so word meanings won't work offline.`, page: 'Dictionaries', href: '#/settings/dictionaries' })
  const voice = lacking('voice')
  if (voice.length > 0) notes.push({ text: `This Mac has no voice for ${list(voice)}, so books won't be read aloud in ${voice.length === 1 ? 'it' : 'them'}.`, page: 'Voices', href: '#/settings/voices' })
  if (notes.length === 0) return { ok: true, text: 'Everything for your languages is available locally.', notes: [] }
  return { ok: false, text: notes.map((n) => n.text).join(' '), notes }
}
