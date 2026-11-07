import { describe, expect, it } from 'vitest'
import { placePopover } from './placement'

const view = { width: 1000, height: 700 }

describe('placePopover', () => {
  it('opens below the button, lined up with its left edge', () => {
    expect(placePopover({ left: 100, right: 140, bottom: 50 }, 300, 'start', view)).toEqual({ top: 56, left: 100, width: 300, maxHeight: 636 })
  })
  it('lines up with the right edge when asked', () => {
    expect(placePopover({ left: 700, right: 740, bottom: 50 }, 300, 'end', view).left).toBe(440)
  })
  it('stays inside the window on both sides', () => {
    expect(placePopover({ left: 900, right: 940, bottom: 50 }, 300, 'start', view).left).toBe(692)
    expect(placePopover({ left: 2, right: 30, bottom: 50 }, 300, 'end', view).left).toBe(8)
  })
  it('shrinks to a narrow window, and keeps a usable height near the bottom', () => {
    expect(placePopover({ left: 10, right: 40, bottom: 50 }, 380, 'start', { width: 320, height: 700 }).width).toBe(304)
    expect(placePopover({ left: 10, right: 40, bottom: 650 }, 300, 'start', view).maxHeight).toBe(160)
  })
})

describe('opening upward', () => {
  it('opens above a button at the bottom of the window, and below one at the top', () => {
    const view = { width: 800, height: 600 }
    const low = placePopover({ left: 400, right: 420, top: 520, bottom: 550 }, 260, 'end', view)
    expect(low.top).toBeUndefined()
    expect(low.bottom).toBe(600 - 520 + 6)
    const high = placePopover({ left: 400, right: 420, top: 40, bottom: 70 }, 260, 'end', view)
    expect(high.top).toBe(76)
  })
})
