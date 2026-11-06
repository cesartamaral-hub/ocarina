import { describe, expect, it } from 'vitest'
import { matching, splitLanguages, toggled } from './languageChoice'

describe('languageChoice', () => {
  it('puts the popular languages first, in order, and the rest alphabetically', () => {
    const { popular, rest } = splitLanguages(['Zulu', 'Polish', 'Afrikaans', 'English', 'Italian'])
    expect(popular).toEqual(['English', 'Italian', 'Polish'])
    expect(rest).toEqual(['Afrikaans', 'Zulu'])
  })
  it('leaves out popular languages that are already added', () => {
    expect(splitLanguages(['Dutch', 'Basque']).popular).toEqual(['Dutch'])
    expect(splitLanguages(['Basque']).popular).toEqual([])
  })
  it('filters by any part of the name, ignoring case', () => {
    expect(matching(['Basque', 'Bosnian', 'Czech'], 'BO')).toEqual(['Bosnian'])
    expect(matching(['Basque'], '  ')).toEqual(['Basque'])
  })
  it('toggles a name in the chosen list', () => {
    expect(toggled(['Dutch'], 'Polish')).toEqual(['Dutch', 'Polish'])
    expect(toggled(['Dutch', 'Polish'], 'Dutch')).toEqual(['Polish'])
  })
})
