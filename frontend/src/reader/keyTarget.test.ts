import { describe, expect, it } from 'vitest'
import { whoGetsTheKey } from './keyTarget'

describe('whoGetsTheKey', () => {
  it('prefers the pointer, then the selection, by default', () => {
    expect(whoGetsTheKey('pointer', true, true)).toBe('pointer')
    expect(whoGetsTheKey('pointer', false, true)).toBe('selected')
    expect(whoGetsTheKey('pointer', true, false)).toBe('pointer')
    expect(whoGetsTheKey('pointer', false, false)).toBeNull()
  })
  it('can prefer the selection', () => {
    expect(whoGetsTheKey('selection', true, true)).toBe('selected')
    expect(whoGetsTheKey('selection', true, false)).toBe('pointer')
  })
  it('can ignore the pointer', () => {
    expect(whoGetsTheKey('selected-only', true, false)).toBeNull()
    expect(whoGetsTheKey('selected-only', true, true)).toBe('selected')
  })
})
