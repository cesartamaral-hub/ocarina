import { describe, expect, it } from 'vitest'
import type { Item } from '../api'
import { effectiveMode, nextMode, pageTranslations } from './translationView'

let n = 0
const word = (sentence: number): Item => ({ text: 'w', display: 'w', isWord: true, termId: null, status: 0, sentence, index: n++ })
const mark = (sentence: number): Item => ({ text: '¶', display: ' ', isWord: false, termId: null, status: 0, sentence, index: n++ })

describe('pageTranslations', () => {
  const paragraphs = [[[word(10)], [word(11)]], [[mark(12)], [word(13)]]] // the sentence 12 has no word
  const sentences = [
    { page: 1, index: 0, translation: 'one', stale: false },
    { page: 1, index: 1, translation: null, stale: false },
    { page: 1, index: 2, translation: 'three', stale: true },
    { page: 2, index: 0, translation: 'elsewhere', stale: false },
  ]

  it('matches translations to sentences with a word, in order, on this page only', () => {
    const found = pageTranslations(paragraphs, sentences, 1)
    expect([...found.keys()]).toEqual([10, 13])
    expect(found.get(10)).toEqual({ text: 'one', stale: false })
    expect(found.get(13)).toEqual({ text: 'three', stale: true })
    expect(found.has(11)).toBe(false) // not translated yet
  })

  it('finds nothing for a page that has none', () => {
    expect(pageTranslations(paragraphs, [], 1).size).toBe(0)
    expect(pageTranslations([], sentences, 1).size).toBe(0)
  })
})

describe('modes', () => {
  it('show the original when the page has no translation', () => {
    expect(effectiveMode('both', false)).toBe('original')
    expect(effectiveMode('both', true)).toBe('both')
  })
  it('go round: original, both, translation, original', () => {
    expect(nextMode('original', true)).toBe('both')
    expect(nextMode('both', true)).toBe('translation')
    expect(nextMode('translation', true)).toBe('original')
    expect(nextMode('both', false)).toBe('original')
  })
})
