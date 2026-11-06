import type { Model } from './api'

// What each kind of model is for, in the words shown next to it (Welcome and Settings → Models), so the two always agree.
const PURPOSE = {
  speech: 'Listening: a more natural voice for your books, or your own voice',
  text: 'Translating sentences locally, offline',
  aligner: 'Syncing your own recordings with the text (highlight, J/L jumps)',
  transcriber: 'Importing YouTube videos that have no captions',
} as const

export const purposeOf = (m: Pick<Model, 'kind' | 'builtin'>): string =>
  m.builtin ? 'Listening: the voice built into your Mac, nothing to download' : PURPOSE[m.kind ?? 'speech']
