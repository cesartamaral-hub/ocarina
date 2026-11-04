import { describe, expect, it } from 'vitest'
import { SIDE_DEFAULT, SIDE_MAX, SIDE_MIN, clampWidth, widthAfterKey } from './sidePanel'

describe('clampWidth', () => {
  it('keeps the panel between its minimum and maximum', () => {
    expect(clampWidth(100)).toBe(SIDE_MIN)
    expect(clampWidth(9999)).toBe(SIDE_MAX)
    expect(clampWidth(400.6)).toBe(401)
  })

  it('survives nonsense saved in the preferences', () => {
    expect(clampWidth(Number.NaN)).toBe(SIDE_DEFAULT)
    expect(clampWidth('wide')).toBe(SIDE_DEFAULT)
    expect(clampWidth(undefined)).toBe(SIDE_DEFAULT)
    expect(clampWidth(Infinity)).toBe(SIDE_DEFAULT)
  })
})

describe('widthAfterKey', () => {
  it('left makes the panel wider, right narrower', () => {
    expect(widthAfterKey('ArrowLeft', 380, false)).toBe(396)
    expect(widthAfterKey('ArrowRight', 380, false)).toBe(364)
  })

  it('shift takes bigger steps', () => {
    expect(widthAfterKey('ArrowLeft', 380, true)).toBe(428)
  })

  it('stops at the limits', () => {
    expect(widthAfterKey('ArrowLeft', SIDE_MAX, false)).toBe(SIDE_MAX)
    expect(widthAfterKey('ArrowRight', SIDE_MIN, true)).toBe(SIDE_MIN)
  })

  it('Home, End and Enter jump to the minimum, the maximum and the default', () => {
    expect(widthAfterKey('Home', 400, false)).toBe(SIDE_MIN)
    expect(widthAfterKey('End', 400, false)).toBe(SIDE_MAX)
    expect(widthAfterKey('Enter', 500, false)).toBe(SIDE_DEFAULT)
  })

  it('ignores other keys', () => {
    expect(widthAfterKey('a', 380, false)).toBeNull()
  })
})
