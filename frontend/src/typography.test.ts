import { describe, expect, it } from 'vitest'
import { DEFAULTS, FONTS, LIMITS, PRESETS, fromPreferences, matchingPreset, measurePx, normalize, spacingLabel, stepSize, toCssVars } from './typography'

describe('normalize', () => {
  it('turns nothing into the defaults', () => {
    expect(normalize(undefined)).toEqual(DEFAULTS)
    expect(normalize(null)).toEqual(DEFAULTS)
    expect(normalize('text')).toEqual(DEFAULTS)
    expect(normalize({})).toEqual(DEFAULTS)
  })

  it('keeps valid values and fills in the rest', () => {
    expect(normalize({ size: 22, font: 'serif', align: 'justify' })).toEqual({ ...DEFAULTS, size: 22, font: 'serif', align: 'justify' })
  })

  it('pulls numbers into their limits and onto their steps', () => {
    const t = normalize({ size: 99, width: 3, line: 1.234, letter: 5, word: -1 })
    expect(t.size).toBe(LIMITS.size.max)
    expect(t.width).toBe(LIMITS.width.min)
    expect(t.line).toBe(LIMITS.line.min)
    expect(t.letter).toBe(LIMITS.letter.max)
    expect(t.word).toBe(LIMITS.word.min)
  })

  it('does not leave floating point dust', () => {
    expect(normalize({ line: 1.7000000000000002 }).line).toBe(1.7)
    expect(normalize({ letter: 0.030000000000000002 }).letter).toBe(0.03)
  })

  it('ignores values of the wrong kind', () => {
    expect(normalize({ size: '20', font: 'comic', weight: 600, width: NaN, line: Infinity, align: 'left' })).toEqual(DEFAULTS)
  })
})

describe('fromPreferences', () => {
  const prefs = (data: Record<string, unknown>) => ({ get: <T,>(key: string, fallback: T) => (key in data ? (data[key] as T) : fallback) })

  it('uses the saved typography object', () => {
    expect(fromPreferences(prefs({ 'reader.typography': { size: 24, weight: 700 } }).get)).toEqual({ ...DEFAULTS, size: 24, weight: 700 })
  })

  it('carries over the size and font of earlier versions', () => {
    expect(fromPreferences(prefs({ readerSize: 26, readerFont: 'serif' }).get)).toEqual({ ...DEFAULTS, size: 26, font: 'serif' })
  })

  it('prefers the new settings once they exist, even when old ones are still there', () => {
    expect(fromPreferences(prefs({ 'reader.typography': DEFAULTS, readerSize: 30 }).get).size).toBe(DEFAULTS.size)
  })

  it('survives a damaged saved value', () => {
    expect(fromPreferences(prefs({ 'reader.typography': 'broken' }).get)).toEqual(DEFAULTS)
  })
})

describe('what the page gets', () => {
  it('keeps the characters per line when the text size changes', () => {
    const small = measurePx({ ...DEFAULTS, size: 16 })
    const big = measurePx({ ...DEFAULTS, size: 32 })
    expect(Math.abs(big - small * 2)).toBeLessThanOrEqual(1)
    expect(measurePx(DEFAULTS)).toBe(Math.round(70 * 18 * FONTS.sans.charWidth))
  })

  it('writes units the browser understands', () => {
    const vars = toCssVars({ ...DEFAULTS, size: 20, letter: 0.05, word: 0.1, line: 1.8, weight: 500, align: 'center' })
    expect(vars['--r-size']).toBe('20px')
    expect(vars['--r-letter']).toBe('0.05em')
    expect(vars['--r-word']).toBe('0.1em')
    expect(vars['--r-line']).toBe('1.8')
    expect(vars['--r-weight']).toBe('500')
    expect(vars['--r-align']).toBe('center')
  })

  it('hyphenates only justified text', () => {
    expect(toCssVars({ ...DEFAULTS, align: 'justify' })['--r-hyphens']).toBe('auto')
    expect(toCssVars({ ...DEFAULTS, align: 'start' })['--r-hyphens']).toBe('manual')
  })
})

describe('small helpers', () => {
  it('steps the text size and stops at the limits', () => {
    expect(stepSize(18, 1)).toBe(19)
    expect(stepSize(18, -1)).toBe(17)
    expect(stepSize(LIMITS.size.max, 1)).toBe(LIMITS.size.max)
    expect(stepSize(LIMITS.size.min, -1)).toBe(LIMITS.size.min)
  })

  it('names spacing in plain terms', () => {
    expect(spacingLabel(0, LIMITS.letter)).toBe('Standard')
    expect(spacingLabel(0.05, LIMITS.letter)).toBe('+5%')
  })
})

describe('presets', () => {
  it('are valid as they are: normalising changes nothing', () => {
    for (const p of PRESETS) expect(normalize(p.values)).toEqual(p.values)
  })
  it('differ from each other', () => {
    expect(new Set(PRESETS.map((p) => JSON.stringify(p.values))).size).toBe(PRESETS.length)
  })
  it('are recognised while nothing is changed, and not after', () => {
    for (const p of PRESETS) expect(matchingPreset(p.values)).toBe(p.id)
    expect(matchingPreset({ ...PRESETS[1].values, size: 17 })).toBeNull()
  })
  it('start with the standard look', () => {
    expect(PRESETS[0].values).toEqual(DEFAULTS)
  })
})
