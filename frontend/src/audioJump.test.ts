import { describe, expect, it } from 'vitest'
import { JUMP_SECONDS, jumpTarget } from './audioJump'

const starts = [0, 4, 9, 15] // four sentences

describe('without timings (your own recordings)', () => {
  it('jumps ten seconds', () => {
    expect(jumpTarget('back', 50, 120, null)).toBe(50 - JUMP_SECONDS)
    expect(jumpTarget('forward', 50, 120, null)).toBe(50 + JUMP_SECONDS)
  })

  it('stays inside the recording', () => {
    expect(jumpTarget('back', 3, 120, null)).toBe(0)
    expect(jumpTarget('forward', 115, 120, null)).toBe(120)
  })

  it('treats an empty list like no timings, and an unknown length as unbounded', () => {
    expect(jumpTarget('forward', 5, 120, [])).toBe(15)
    expect(jumpTarget('forward', 5, NaN, null)).toBe(15)
    expect(jumpTarget('back', 5, 0, null)).toBe(0)
  })
})

describe('with sentence timings', () => {
  it('back restarts the sentence you are in', () => {
    expect(jumpTarget('back', 11.5, 30, starts)).toBe(9)
  })

  it('back goes to the previous sentence when you have only just started this one', () => {
    expect(jumpTarget('back', 9.4, 30, starts)).toBe(4)
    expect(jumpTarget('back', 9, 30, starts)).toBe(4) // exactly at the start counts as just started
  })

  it('pressing back twice quickly walks backwards through the sentences', () => {
    const first = jumpTarget('back', 11.5, 30, starts) // restart sentence 3 at 9
    expect(jumpTarget('back', first, 30, starts)).toBe(4) // then the one before
    expect(jumpTarget('back', 4, 30, starts)).toBe(0)
  })

  it('back at the very start stays there', () => {
    expect(jumpTarget('back', 0.3, 30, starts)).toBe(0)
    expect(jumpTarget('back', 0, 30, starts)).toBe(0)
  })

  it('forward goes to the next sentence', () => {
    expect(jumpTarget('forward', 0, 30, starts)).toBe(4)
    expect(jumpTarget('forward', 10, 30, starts)).toBe(15)
  })

  it('forward from the last sentence goes to the end', () => {
    expect(jumpTarget('forward', 20, 30, starts)).toBe(30)
  })

  it('before the first start time, back goes to 0 and forward to the first sentence', () => {
    expect(jumpTarget('back', 1, 30, [2, 6])).toBe(0)
    expect(jumpTarget('forward', 1, 30, [2, 6])).toBe(2)
  })
})
