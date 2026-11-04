import { describe, expect, it } from 'vitest'
import { growthPoints, relativeDay, visibleLanguages } from './readingStats'

const today = new Date(2026, 10, 5) // 5 November 2026

describe('relativeDay', () => {
  it('speaks of today and yesterday', () => {
    expect(relativeDay('2026-11-05', today)).toBe('today')
    expect(relativeDay('2026-11-04', today)).toBe('yesterday')
  })
  it('counts days for a month, then gives the date', () => {
    expect(relativeDay('2026-10-30', today)).toBe('6 days ago')
    expect(relativeDay('2026-09-01', today)).toMatch(/1 Sept|Sep 1|1 Sep/)
    expect(relativeDay('2025-03-02', today)).toMatch(/2025/)
  })
  it('has an answer for a language never read', () => {
    expect(relativeDay(null, today)).toBe('never')
  })
})

describe('visibleLanguages', () => {
  const all = [{ id: 1 }, { id: 2 }, { id: 3 }]
  it('shows everything, or the chosen language', () => {
    expect(visibleLanguages(all, 'all')).toEqual(all)
    expect(visibleLanguages(all, '2')).toEqual([{ id: 2 }])
  })
  it('falls back to everything when the chosen language is gone', () => {
    expect(visibleLanguages(all, '9')).toEqual(all)
  })
})

describe('growthPoints', () => {
  it('starts from zero on the first day', () => {
    expect(growthPoints([{ date: '2026-10-01', known: 5 }, { date: '2026-10-03', known: 9 }])).toEqual([
      { label: '2026-10-01', value: 0 },
      { label: '2026-10-01', value: 5 },
      { label: '2026-10-03', value: 9 },
    ])
  })
  it('is empty with nothing known', () => {
    expect(growthPoints([])).toEqual([])
  })
})
