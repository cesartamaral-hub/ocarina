import { describe, expect, it } from 'vitest'
import { SPEED_PRESETS, clampSpeed, presetFor, speedLabel } from './speeds'

describe('clampSpeed', () => {
  it('keeps valid speeds and snaps to the slider steps', () => {
    expect(clampSpeed(1)).toBe(1)
    expect(clampSpeed(0.85)).toBe(0.85)
    expect(clampSpeed(1.23)).toBe(1.25)
  })
  it('pulls speeds into the range', () => {
    expect(clampSpeed(0.1)).toBe(0.5)
    expect(clampSpeed(5)).toBe(2)
  })
  it('has an answer for anything that is not a number', () => {
    expect(clampSpeed(undefined)).toBe(1)
    expect(clampSpeed('fast')).toBe(1)
    expect(clampSpeed(NaN)).toBe(1)
  })
  it('accepts every preset as it is', () => {
    for (const p of SPEED_PRESETS) expect(clampSpeed(p)).toBe(p)
  })
})

describe('presetFor and speedLabel', () => {
  it('marks a preset only when the speed is exactly one', () => {
    expect(presetFor(0.75)).toBe(0.75)
    expect(presetFor(0.8)).toBeUndefined()
  })
  it('writes two decimals', () => {
    expect(speedLabel(2)).toBe('2.00×')
    expect(speedLabel(0.5)).toBe('0.50×')
  })
})
