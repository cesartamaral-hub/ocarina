import { describe, expect, it } from 'vitest'
import { shouldLookUpOnline } from './autoLookup'

const on = { offline: false, enabled: true }

describe('shouldLookUpOnline', () => {
  it('asks for a word or a short expression', () => {
    expect(shouldLookUpOnline({ ...on, text: 'huis' })).toBe(true)
    expect(shouldLookUpOnline({ ...on, text: 'ook al is hij' })).toBe(true)
  })
  it('does not ask while offline or when the setting is off', () => {
    expect(shouldLookUpOnline({ offline: true, enabled: true, text: 'huis' })).toBe(false)
    expect(shouldLookUpOnline({ offline: false, enabled: false, text: 'huis' })).toBe(false)
  })
  it('leaves numbers, punctuation and long selections to the button', () => {
    expect(shouldLookUpOnline({ ...on, text: '1995' })).toBe(false)
    expect(shouldLookUpOnline({ ...on, text: '…' })).toBe(false)
    expect(shouldLookUpOnline({ ...on, text: 'een twee drie vier vijf' })).toBe(false)
  })
})
