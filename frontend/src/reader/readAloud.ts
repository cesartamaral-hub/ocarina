import type { ReaderPage } from '../api'

export type ReadSentence = { id: number; text: string }

// The sentences of a page that have words, in order, with their text: what is read aloud (the same ones the audio follows).
export function readableSentences(page: ReaderPage): ReadSentence[] {
  return page.paragraphs
    .flat()
    .filter((s) => s.some((i) => i.isWord))
    .map((s) => ({
      id: s[0].sentence,
      text: s
        .map((i) => i.text)
        .join('')
        .replace(/\s+/g, ' ')
        .trim(),
    }))
    .filter((s) => s.text !== '')
}

// Where reading starts: the sentence asked for if the page has it, else the first.
export const startIndex = (sentences: ReadSentence[], from?: number) =>
  Math.max(
    0,
    sentences.findIndex((s) => s.id === from),
  )
