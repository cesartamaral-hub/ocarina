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

// The features the optional downloads add, in plain words (the model's own name stays in the tooltip): a title, one short line, and how
// the footer line on the Books page says it is not set up yet.
export type Feature = { title: string; line: string; missing: string }
const FEATURE: Record<NonNullable<Model['kind']>, Feature> = {
  text: { title: 'Translate sentences offline', line: 'Translations that work without the internet.', missing: "Offline translation isn't set up yet" },
  speech: { title: 'A more natural voice', line: 'Books read in a natural voice, or in your own.', missing: "The better voice isn't set up yet" },
  aligner: { title: 'Sync your own recordings', line: 'The text follows a recording you add.', missing: "Recording sync isn't set up yet" },
  transcriber: { title: 'Transcribe videos without captions', line: 'Turns what is said in a video into text.', missing: "Video transcription isn't set up yet" },
}
export const featureOf = (m: Pick<Model, 'kind'>): Feature => FEATURE[m.kind ?? 'speech']
