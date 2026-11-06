import { describe, expect, it } from 'vitest'
import { alphabetical, matching, moved, toggled } from './languageChoice'

describe('languageChoice', () => {
  it('sorts alphabetically without changing the original', () => {
    const names = ['Zulu', 'Dutch', 'Afrikaans']
    expect(alphabetical(names)).toEqual(['Afrikaans', 'Dutch', 'Zulu'])
    expect(names[0]).toBe('Zulu')
  })
  it('filters by any part of the name, ignoring case', () => {
    expect(matching(['Basque', 'Bosnian', 'Czech'], 'BO')).toEqual(['Bosnian'])
    expect(matching(['Basque'], '  ')).toEqual(['Basque'])
  })
  it('toggles a name in the chosen list', () => {
    expect(toggled(['Dutch'], 'Polish')).toEqual(['Dutch', 'Polish'])
    expect(toggled(['Dutch', 'Polish'], 'Dutch')).toEqual(['Polish'])
  })
  it('moves the highlight with the arrow keys and stops at the ends', () => {
    expect(moved(0, 'ArrowDown', 3)).toBe(1)
    expect(moved(2, 'ArrowDown', 3)).toBe(2)
    expect(moved(0, 'ArrowUp', 3)).toBe(0)
    expect(moved(0, 'ArrowDown', 0)).toBe(0)
  })
})
