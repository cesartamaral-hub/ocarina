import { describe, expect, it } from 'vitest'
import { audioSeconds, formatEstimate, sentencesToTranslate, timeLeft, translationSeconds } from './estimate'

const s = (page: number, translation: string | null, stale = false) => ({ page, index: 0, translation, stale })

describe('estimates', () => {
  it('words a time in a few steps', () => {
    expect(formatEstimate(0)).toBe('')
    expect(formatEstimate(20)).toBe('under a minute')
    expect(formatEstimate(240)).toBe('about 4 min')
    expect(formatEstimate(5400)).toBe('about 1.5 hours')
  })
  it('works out audio time from text length and the voice speed', () => {
    expect(audioSeconds(1400, 0.5)).toBe(50)
  })
  it('counts what a run would translate', () => {
    const all = [s(1, 'a'), s(1, null), s(2, 'b', true), s(2, 'c')]
    expect(sentencesToTranslate(all)).toBe(2)
    expect(sentencesToTranslate(all, 1)).toBe(1)
    expect(sentencesToTranslate(all, 2, true)).toBe(2)
    expect(translationSeconds(10, { secondsPerSentence: 2 })).toBe(20)
    expect(translationSeconds(10, undefined)).toBe(0)
  })
  it('gives the time left from the pace so far', () => {
    expect(timeLeft(10, 0, 20)).toBe('')
    expect(timeLeft(60, 10, 20)).toBe('about 1 min left')
    expect(timeLeft(10, 18, 20)).toBe('under a minute left')
  })
})
