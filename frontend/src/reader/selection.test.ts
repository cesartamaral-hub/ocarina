import { describe, expect, it } from 'vitest'
import { PHRASE_MAX_WORDS, classify, type Piece } from './selection'

const words = (n: number, sentence = 0): Piece[] =>
  Array.from({ length: n }, (_, i) => [
    { isWord: true, sentence, display: `w${i}` },
    { isWord: false, sentence, display: i < n - 1 ? '  ' : '' },
  ]).flat()

describe('classify', () => {
  it('ignores a single word', () => {
    expect(classify(words(1))).toBeNull()
    expect(classify([])).toBeNull()
  })

  it('treats a few words in one sentence as a phrase', () => {
    expect(classify(words(2))?.kind).toBe('phrase')
    expect(classify(words(PHRASE_MAX_WORDS))?.kind).toBe('phrase')
  })

  it('treats a longer run as text', () => {
    expect(classify(words(PHRASE_MAX_WORDS + 1))?.kind).toBe('text')
  })

  it('treats a run across a sentence end as text, even when short', () => {
    expect(classify([...words(2, 0), ...words(2, 1)])?.kind).toBe('text')
  })

  it('joins the pieces with single spaces and names the first sentence', () => {
    expect(classify(words(3, 4))).toEqual({ kind: 'phrase', text: 'w0 w1 w2', sentence: 4 })
  })
})
