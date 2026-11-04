import { describe, expect, it } from 'vitest'
import { wordTime } from './wordTime'

describe('wordTime', () => {
  it('is the start of the sentence for its first word', () => {
    expect(wordTime(10, 14, 0, 40)).toBe(10)
  })
  it('finds a word in proportion to the letters before it', () => {
    expect(wordTime(10, 14, 20, 40)).toBeCloseTo(12) // half way through 4 s
  })
  it('does not stretch over the pause after a sentence', () => {
    // 40 letters is at most 4 s of speech; the next sentence only starts 10 s later
    expect(wordTime(10, 20, 20, 40)).toBeCloseTo(12)
  })
  it('copes with the last sentence, which has no next start', () => {
    expect(wordTime(10, undefined, 10, 40)).toBeCloseTo(11)
  })
  it('copes with an empty sentence', () => {
    expect(wordTime(10, 12, 0, 0)).toBe(10)
  })
})
