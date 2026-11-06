import type { Model } from './api'

// What each kind of model is for, in the words shown next to it (Welcome and Settings → Models), so the two always agree.
const PURPOSE = {
  speech: 'Listening: reads your books aloud',
  text: 'Translating sentences locally, offline',
  aligner: 'Syncing your own recordings with the text (highlight, J/L jumps)',
  transcriber: 'Importing YouTube videos that have no captions',
} as const

export const purposeOf = (m: Pick<Model, 'kind'>): string => PURPOSE[m.kind ?? 'speech']
