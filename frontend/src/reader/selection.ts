// What dragging across the text means: a few words in one sentence are a phrase you can learn; anything longer,
// or across a sentence end, is text you read, translate or play.
export const PHRASE_MAX_WORDS = 6

export type Piece = { isWord: boolean; sentence: number; display: string }
export type Picked = { kind: 'phrase' | 'text'; text: string; sentence: number }

export function classify(pieces: Piece[]): Picked | null {
  const words = pieces.filter((p) => p.isWord)
  if (words.length < 2) return null
  const text = pieces.map((p) => p.display).join('').replace(/\s+/g, ' ').trim()
  const oneSentence = words.every((w) => w.sentence === words[0].sentence)
  return { kind: oneSentence && words.length <= PHRASE_MAX_WORDS ? 'phrase' : 'text', text, sentence: words[0].sentence }
}
