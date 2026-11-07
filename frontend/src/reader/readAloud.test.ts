import { describe, expect, it } from 'vitest'
import { startIndex } from './readAloud'

const sentences = [
  { id: 4, text: 'Een.' },
  { id: 7, text: 'Twee.' },
  { id: 9, text: 'Drie.' },
]

describe('startIndex', () => {
  it('starts at the sentence asked for', () => expect(startIndex(sentences, 7)).toBe(1))
  it('starts at the top without one, or when the page does not have it', () => {
    expect(startIndex(sentences)).toBe(0)
    expect(startIndex(sentences, 99)).toBe(0)
  })
})
