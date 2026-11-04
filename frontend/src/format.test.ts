import { describe, expect, it } from 'vitest'
import { formatBytes } from './format'

describe('formatBytes', () => {
  it('uses the unit that keeps the number short', () => {
    expect(formatBytes(9_330_000_000)).toBe('9.3 GB')
    expect(formatBytes(2_280_000)).toBe('2.3 MB')
    expect(formatBytes(15_400_000)).toBe('15 MB')
    expect(formatBytes(380_000)).toBe('380 KB')
  })
  it('never shows a small file as zero', () => {
    expect(formatBytes(0)).toBe('0 KB')
    expect(formatBytes(40)).toBe('1 KB')
  })
})
