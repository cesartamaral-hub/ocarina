import { describe, expect, it } from 'vitest'
import { LEVELS, progressFor } from './cefr'

describe('progressFor', () => {
  it('is A0 below the first level, working towards A1', () => {
    const p = progressFor(125)
    expect(p.label).toBe('A0')
    expect(p.level).toBeNull()
    expect(p.next?.id).toBe('A1')
    expect(p.toNext).toBe(375)
    expect(p.fraction).toBeCloseTo(0.25)
    expect(p.segments[0]).toBeCloseTo(0.25)
    expect(p.segments.slice(1).every((s) => s === 0)).toBe(true)
  })

  it('reaches a level at its words, and starts on the next stretch', () => {
    const p = progressFor(500)
    expect(p.label).toBe('A1')
    expect(p.next?.id).toBe('A2')
    expect(p.fraction).toBe(0)
    expect(p.segments[0]).toBe(1)
  })

  it('finds how far through a stretch', () => {
    const p = progressFor(1840)
    expect(p.label).toBe('A2')
    expect(p.next?.id).toBe('B1')
    expect(p.toNext).toBe(660)
    expect(p.fraction).toBeCloseTo((1840 - 1200) / (2500 - 1200))
    expect(p.segments.map((s) => Math.round(s * 100))).toEqual([100, 100, 49, 0, 0, 0])
  })

  it('has nowhere further to go at C2', () => {
    const p = progressFor(20000)
    expect(p.label).toBe('C2')
    expect(p.next).toBeNull()
    expect(p.toNext).toBe(0)
    expect(p.fraction).toBe(1)
    expect(p.segments).toEqual([1, 1, 1, 1, 1, 1])
  })

  it('copes with nothing and with odd numbers', () => {
    expect(progressFor(0).label).toBe('A0')
    expect(progressFor(-5).fraction).toBe(0)
    expect(progressFor(1199.9).label).toBe('A1')
  })

  it('lists the levels in order, each needing more words', () => {
    expect(LEVELS.map((l) => l.id)).toEqual(['A1', 'A2', 'B1', 'B2', 'C1', 'C2'])
    expect(LEVELS.every((l, i) => i === 0 || l.words > LEVELS[i - 1].words)).toBe(true)
  })
})
