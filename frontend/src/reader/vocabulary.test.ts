import { describe, expect, it } from 'vitest'
import { pageVocabulary, vocabularyBar, type WordLike } from './vocabulary'

let n = 0
const w = (text: string, status: number): WordLike => ({ text, isWord: true, status, index: n++, termId: status ? n : null, sentence: 0 })
const gap = (): WordLike => ({ text: ' ', isWord: false, status: 0, index: n++, termId: null, sentence: 0 })

describe('pageVocabulary', () => {
  it('counts running and different words per kind', () => {
    n = 0
    const v = pageVocabulary([w('de', 5), gap(), w('De', 5), w('huis', 4), w('hond', 2), w('hond', 2), w('kat', 1), w('Fiets', 0), w('fiets', 0), w('xyz', 98)])
    expect(v.words).toBe(9)
    expect(v.unique).toBe(6)
    expect(v.known).toEqual({ running: 3, unique: 2 })
    expect(v.learning.running).toBe(3)
    expect(v.learning.unique).toBe(2)
    expect(v.learning.byStatus).toEqual({ 1: 1, 2: 1, 3: 0 })
    expect(v.fresh).toEqual({ running: 2, unique: 1 })
    expect(v.ignored).toEqual({ running: 1, unique: 1 })
  })

  it('leaves ignored words out of the known share', () => {
    n = 0
    const v = pageVocabulary([w('a', 5), w('b', 5), w('c', 0), w('d', 0), w('e', 98), w('f', 98)])
    expect(v.knownPercent).toBe(50)
  })

  it('reads well-known (99) as known and rates the page', () => {
    n = 0
    const items = [...Array.from({ length: 49 }, (_, i) => w(`w${i}`, 99)), w('rare', 0)]
    const v = pageVocabulary(items)
    expect(v.known.running).toBe(49)
    expect(v.knownPercent).toBe(98)
  })

  it('lists new words most frequent first, with where they first appear', () => {
    n = 0
    const items = [w('a', 5), w('zon', 0), w('maan', 0), w('Maan', 0), w('ster', 0), w('maan', 0), w('zon', 0)]
    const list = pageVocabulary(items).newWords
    expect(list.map((x) => [x.text, x.count])).toEqual([
      ['maan', 3],
      ['zon', 2],
      ['ster', 1],
    ])
    expect(list[0].index).toBe(2) // first place of "maan"
    expect(list[1].text).toBe('zon')
  })

  it('has a sensible answer for an empty page and for one with nothing but ignored words', () => {
    n = 0
    expect(pageVocabulary([]).knownPercent).toBe(100)
    expect(pageVocabulary([w('x', 98)]).knownPercent).toBe(100)
    expect(pageVocabulary([]).newWords).toEqual([])
  })

  it('estimates reading time from the running words', () => {
    n = 0
    expect(pageVocabulary(Array.from({ length: 300 }, (_, i) => w(`w${i}`, 5))).minutes).toBe(2)
  })
})

describe('vocabularyBar', () => {
  it('adds up to 100 without the ignored words', () => {
    n = 0
    const v = pageVocabulary([w('a', 5), w('b', 2), w('c', 0), w('d', 0), w('e', 98)])
    const bar = vocabularyBar(v)
    expect(bar.known + bar.learning + bar.fresh).toBeCloseTo(100)
    expect(bar.known).toBe(25)
    expect(bar.fresh).toBe(50)
  })
  it('shows an empty page as all known', () => {
    expect(vocabularyBar(pageVocabulary([]))).toEqual({ known: 100, learning: 0, fresh: 0 })
  })
})
