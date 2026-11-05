import { describe, expect, it } from 'vitest'
import { GROUPS, SECTIONS, legacyRedirect, parseSettings, sectionHash } from './settingsRoutes'

describe('parseSettings', () => {
  it('finds the section and what follows it', () => {
    expect(parseSettings('#/settings/appearance')).toEqual({ section: 'appearance', rest: '' })
    expect(parseSettings('#/settings/general')).toEqual({ section: 'general', rest: '' })
    expect(parseSettings('#/settings/languages/12')).toEqual({ section: 'languages', rest: '12' })
    expect(parseSettings('#/settings/languages/new')).toEqual({ section: 'languages', rest: 'new' })
  })
  it('does not know other addresses or unknown sections', () => {
    expect(parseSettings('#/settings')).toBeNull()
    expect(parseSettings('#/settings/nope')).toBeNull()
    expect(parseSettings('#/terms')).toBeNull()
  })
})

describe('legacyRedirect', () => {
  it('sends the old pages to their sections', () => {
    expect(legacyRedirect('#/appearance')).toBe('#/settings/appearance')
    expect(legacyRedirect('#/translation')).toBe('#/settings/translation')
    expect(legacyRedirect('#/languages')).toBe('#/settings/languages')
    expect(legacyRedirect('#/languages/new')).toBe('#/settings/languages/new')
    expect(legacyRedirect('#/languages/7')).toBe('#/settings/languages/7')
  })
  it('opens the section you were in when Settings itself is asked for', () => {
    expect(legacyRedirect('#/settings')).toBe('#/settings/general')
    expect(legacyRedirect('#/settings', 'backups')).toBe('#/settings/backups')
    expect(legacyRedirect('#/settings', 'garbage')).toBe('#/settings/general')
  })
  it('leaves current addresses alone', () => {
    expect(legacyRedirect('#/settings/storage')).toBeNull()
    expect(legacyRedirect('#/book/3/read/1')).toBeNull()
    expect(legacyRedirect('#/terms')).toBeNull()
  })
})

describe('the sections', () => {
  it('are each in a group, once', () => {
    expect(new Set(SECTIONS.map((s) => s.id)).size).toBe(SECTIONS.length)
    expect(GROUPS).toEqual(['', 'Reading', 'Languages', 'Audio and translation', 'Library', 'About'])
    expect(sectionHash('models')).toBe('#/settings/models')
  })
})
