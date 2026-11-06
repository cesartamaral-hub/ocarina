import type { Item, TranslatedSentence } from '../api'

// How a page shows its translation: the original only, the original beside the translation, or the translation only.
export type TranslationMode = 'original' | 'both' | 'translation'
export const MODES: TranslationMode[] = ['original', 'both', 'translation']

export type PageTranslation = { text: string; stale: boolean }

// The translation of each sentence of a page, by the sentence's number on the page. A page's sentences that contain a word are
// the ones a book's translation (and its audio) counts, in order, so the i-th of them has translation index i.
export function pageTranslations(paragraphs: Item[][][], sentences: TranslatedSentence[], page: number): Map<number, PageTranslation> {
  const byIndex = new Map(sentences.filter((s) => s.page === page && s.translation !== null).map((s) => [s.index, s]))
  const found = new Map<number, PageTranslation>()
  let index = 0
  for (const para of paragraphs) {
    for (const sent of para) {
      if (!sent.some((i) => i.isWord)) continue
      const t = byIndex.get(index++)
      if (t) found.set(sent[0].sentence, { text: t.translation!, stale: t.stale })
    }
  }
  return found
}

// What is shown: the chosen mode, or the original while this page has no translation to show.
export const effectiveMode = (chosen: TranslationMode, pageHasTranslation: boolean): TranslationMode => (pageHasTranslation ? chosen : 'original')

// When a translation job finishes and the current page has a translation, someone reading the original gets the two columns (original
// beside translation). Anyone already looking at the translation, or at both, stays where they are.
export const modeAfterJob = (chosen: TranslationMode, pageHasTranslation: boolean): TranslationMode => (chosen === 'original' && pageHasTranslation ? 'both' : chosen)

// The key that goes through the modes; with no translation on the page it stays on the original.
export function nextMode(current: TranslationMode, pageHasTranslation: boolean): TranslationMode {
  if (!pageHasTranslation) return 'original'
  return MODES[(MODES.indexOf(current) + 1) % MODES.length]
}
