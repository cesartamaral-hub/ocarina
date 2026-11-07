import { describe, expect, it } from 'vitest'
import { isNumberText, wordsOf } from './numberText'

describe('isNumberText', () => {
  it('knows digits, decimals, thousands and ordinals', () => {
    for (const t of ['1995', '3', '2,5', '1.250', '3e', '1er']) expect(isNumberText(t)).toBe(true)
  })
  it('leaves words and punctuation alone', () => {
    for (const t of ['huis', ',', '', 'abc1', ' ']) expect(isNumberText(t)).toBe(false)
  })
})

describe('wordsOf', () => {
  it('splits a written number into its distinct words', () => {
    expect(wordsOf('negentien honderd vijfennegentig')).toEqual(['negentien', 'honderd', 'vijfennegentig'])
    expect(wordsOf('quatre-vingt-quinze')).toEqual(['quatre', 'vingt', 'quinze'])
    expect(wordsOf('twee honderd twee')).toEqual(['twee', 'honderd'])
  })
})
