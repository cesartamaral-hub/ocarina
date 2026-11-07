import type { TranslatedSentence, TranslationMethod } from './api'

// Rough times for the "about 3 min" shown before a job starts, and the time left while it runs. Always an estimate, never exact.

const SPOKEN_CHARS_PER_SECOND = 14 // how much text a voice says in a second

// "about 4 min", "under a minute", "about 1.5 hours"
export function formatEstimate(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds <= 0) return ''
  if (seconds < 45) return 'under a minute'
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `about ${minutes} min`
  return `about ${(seconds / 3600).toFixed(1)} hours`
}

// Making audio for this much text with a model that needs `perAudioSecond` seconds for each second of speech.
export const audioSeconds = (chars: number, perAudioSecond: number): number => (chars / SPOKEN_CHARS_PER_SECOND) * perAudioSecond

// The sentences a run would translate: those without a (current) translation, or all of them when translating again. `page` limits to one page.
export function sentencesToTranslate(all: TranslatedSentence[], page?: number, again = false): number {
  return all.filter((s) => (page === undefined || s.page === page) && (again || s.translation === null || s.stale)).length
}

export const translationSeconds = (sentences: number, method: Pick<TranslationMethod, 'secondsPerSentence'> | undefined): number =>
  method ? sentences * method.secondsPerSentence : 0

// Time left from the pace so far; '' until a sentence is done (nothing to go on yet).
export function timeLeft(elapsedSeconds: number, done: number, total: number): string {
  if (done <= 0 || total <= done || elapsedSeconds <= 0) return ''
  const seconds = (elapsedSeconds / done) * (total - done)
  return seconds < 45 ? 'under a minute left' : `${formatEstimate(seconds)} left`
}
