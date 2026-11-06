import type { Model } from './api'

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
