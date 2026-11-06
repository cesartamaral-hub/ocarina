import { describe, expect, it } from 'vitest'
import type { Readiness } from './api'
import { offlineSummary } from './offlineReadiness'

const ok = { ok: true, names: [] }
const no = { ok: false, names: [] }
const base = (languages: Readiness['languages']): Readiness => ({ offline: false, languages, audioSync: { ok: false, name: '' } })

describe('offlineSummary', () => {
  it('is ready when every language has all three', () => {
    expect(offlineSummary(base([{ code: 'nl', name: 'Dutch', dictionary: ok, translation: ok, voice: ok }]))).toEqual({ ok: true, text: 'Everything for your languages is available locally.', notes: [] })
  })
  it('suggests the models page when none of the languages has a translation model', () => {
    const r = offlineSummary(base([{ code: 'pl', name: 'Polish', dictionary: ok, translation: no, voice: ok }]))
    expect(r.ok).toBe(false)
    expect(r.notes).toEqual([{ text: "You have no local translation model downloaded, so translation won't work offline.", page: 'Models', href: '#/settings/models' }])
  })
  it('names the languages when only some are missing something', () => {
    const r = offlineSummary(
      base([
        { code: 'nl', name: 'Dutch', dictionary: ok, translation: ok, voice: ok },
        { code: 'pl', name: 'Polish', dictionary: no, translation: no, voice: no },
        { code: 'fr', name: 'French', dictionary: ok, translation: no, voice: ok },
      ]),
    )
    expect(r.notes.map((n) => n.text)).toEqual([
      "There is no local translation model for Polish and French, so translating them won't work offline.",
      "There is no dictionary for Polish on this Mac, so word meanings won't work offline.",
      "This Mac has no voice for Polish, so books won't be read aloud in it.",
    ])
    expect(r.notes.map((n) => n.page)).toEqual(['Models', 'Dictionaries', 'Voices'])
  })
  it('says nothing without languages', () => {
    expect(offlineSummary(base([])).text).toBe('')
  })
})
