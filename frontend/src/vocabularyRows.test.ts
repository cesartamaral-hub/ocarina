import { describe, expect, it } from 'vitest'
import { contextParts, languageAbbr, moveActive, timeAgo } from './vocabularyRows'

describe('languageAbbr', () => {
  it('uses the code of a known language, or the first two letters', () => {
    expect(languageAbbr('Dutch')).toBe('NL')
    expect(languageAbbr('Polski')).toBe('PL')
    expect(languageAbbr('Français')).toBe('FR')
    expect(languageAbbr('German')).toBe('GE')
  })
})

describe('contextParts', () => {
  it('marks the word wherever it is, ignoring case', () => {
    expect(contextParts('Ik woon in Nederland. Nederland is mooi.', 'nederland')).toEqual([
      { text: 'Ik woon in ', bold: false },
      { text: 'Nederland', bold: true },
      { text: '. ', bold: false },
      { text: 'Nederland', bold: true },
      { text: ' is mooi.', bold: false },
    ])
  })
  it('does not mark a word inside another word', () => {
    expect(contextParts('Het huisje is klein', 'huis')).toEqual([{ text: 'Het huisje is klein', bold: false }])
  })
  it('marks a phrase, with letters from other alphabets', () => {
    expect(contextParts('Dzień dobry wszystkim', 'dzień dobry')[0]).toEqual({ text: 'Dzień dobry', bold: true })
  })
  it('is safe with characters that mean something in a pattern', () => {
    const parts = contextParts('Kost het 5 (euro)?', '(euro)')
    expect(parts.map((p) => p.text).join('')).toBe('Kost het 5 (euro)?')
    expect(parts.some((p) => p.bold)).toBe(true)
    expect(contextParts('anything', '')).toEqual([{ text: 'anything', bold: false }])
  })
})

describe('timeAgo', () => {
  const now = new Date('2026-11-10T12:00:00')
  it('says it in the largest sensible unit', () => {
    expect(timeAgo('2026-11-10 08:00:00', now)).toBe('today')
    expect(timeAgo('2026-11-09 08:00:00', now)).toBe('yesterday')
    expect(timeAgo('2026-11-05 08:00:00', now)).toBe('5 days ago')
    expect(timeAgo('2026-10-20 08:00:00', now)).toBe('3 weeks ago')
    expect(timeAgo('2026-07-10 08:00:00', now)).toBe('4 months ago')
    expect(timeAgo('2025-01-10 08:00:00', now)).toBe('a year ago')
    expect(timeAgo(null, now)).toBe('')
  })
})

describe('moveActive', () => {
  const ids = [10, 20, 30]
  it('moves down and up, and stops at the ends', () => {
    expect(moveActive(ids, 10, 'ArrowDown')).toBe(20)
    expect(moveActive(ids, 30, 'ArrowDown')).toBe(30)
    expect(moveActive(ids, 20, 'ArrowUp')).toBe(10)
    expect(moveActive(ids, 10, 'ArrowUp')).toBe(10)
  })
  it('starts at the first row when none is active', () => {
    expect(moveActive(ids, null, 'ArrowDown')).toBe(10)
    expect(moveActive(ids, null, 'ArrowUp')).toBe(10)
  })
  it('jumps to the ends, and copes with an empty list', () => {
    expect(moveActive(ids, 20, 'Home')).toBe(10)
    expect(moveActive(ids, 20, 'End')).toBe(30)
    expect(moveActive([], null, 'ArrowDown')).toBeNull()
  })
})
