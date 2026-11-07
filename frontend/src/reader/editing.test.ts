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

import { countMatches, joinPages, nextMatch, pageAt, replaceAll, splitPages } from './editing'

describe('pages as one text', () => {
  it('joins pages with a visible break line and splits them back', () => {
    const pages = ['Een.\n\nTwee.', 'Drie.']
    expect(splitPages(joinPages(pages))).toEqual(pages)
  })
  it('drops empty pages, so deleting the text between two breaks joins nothing and adds nothing', () => {
    expect(splitPages('Een.\n\n~~~ page break ~~~\n\n\n~~~ page break ~~~\nDrie.')).toEqual(['Een.', 'Drie.'])
  })
  it('makes a single page from text without a break, and none from nothing', () => {
    expect(splitPages('Alles.')).toEqual(['Alles.'])
    expect(splitPages('  \n ')).toEqual([])
  })
  it('tells the page of a position', () => {
    const text = joinPages(['Een.', 'Twee.', 'Drie.'])
    expect(pageAt(text, 0)).toBe(1)
    expect(pageAt(text, text.indexOf('Twee'))).toBe(2)
    expect(pageAt(text, text.length)).toBe(3)
  })
})

describe('find and replace', () => {
  it('counts and replaces, ignoring case unless asked', () => {
    expect(countMatches('Huis huis HUIS', 'huis', false)).toBe(3)
    expect(countMatches('Huis huis HUIS', 'huis', true)).toBe(1)
    expect(replaceAll('Huis huis', 'huis', 'huisje', false)).toBe('huisje huisje')
  })
  it('takes special characters literally and keeps $ in the replacement', () => {
    expect(replaceAll('a.b a.b', 'a.b', '$&', true)).toBe('$& $&')
    expect(countMatches('axb a.b', 'a.b', true)).toBe(1)
  })
  it('finds the next match and wraps round', () => {
    expect(nextMatch('een twee een', 'een', 1, true)).toBe(9)
    expect(nextMatch('een twee een', 'een', 10, true)).toBe(0)
    expect(nextMatch('een', 'zes', 0, true)).toBe(-1)
  })
})
