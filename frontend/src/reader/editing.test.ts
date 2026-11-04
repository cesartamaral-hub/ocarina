import { describe, expect, it } from 'vitest'
import { isDirty, paragraphCount, wordCount } from './editing'

describe('wordCount', () => {
  it('counts words in several scripts and ignores punctuation', () => {
    expect(wordCount('Hallo! Mijn naam is Carla.')).toBe(5)
    expect(wordCount('Każdego ranka wstaję wcześnie.')).toBe(4)
    expect(wordCount('Je m’appelle Léa, et toi ?')).toBe(5)
  })
  it('keeps hyphenated words and numbers whole', () => {
    expect(wordCount('un porte-monnaie de 12 euros')).toBe(5)
  })
  it('is zero for nothing', () => {
    expect(wordCount('')).toBe(0)
    expect(wordCount(' \n ... \n')).toBe(0)
  })
})

describe('paragraphCount', () => {
  it('counts blocks separated by blank lines', () => {
    expect(paragraphCount('Een.\n\nTwee.\n\n\nDrie.')).toBe(3)
    expect(paragraphCount('Een\nnog een regel')).toBe(1)
    expect(paragraphCount('')).toBe(0)
  })
})

describe('isDirty', () => {
  it('sees a real change', () => expect(isDirty('Hallo', 'Hallo!')).toBe(true))
  it('ignores line endings and trailing space', () => {
    expect(isDirty('a\r\nb\n', 'a\nb')).toBe(false)
  })
})
