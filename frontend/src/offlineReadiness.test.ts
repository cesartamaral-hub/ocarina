import { describe, expect, it } from 'vitest'
import type { Readiness } from './api'
import { offlineSummary } from './offlineReadiness'

const ok = { ok: true, names: [] }
const no = { ok: false, names: [] }
const base = (languages: Readiness['languages']): Readiness => ({ offline: false, languages, audioSync: { ok: false, name: '' } })

describe('offlineSummary', () => {
  it('is ready when every language has all three', () => {
    expect(offlineSummary(base([{ code: 'nl', name: 'Dutch', dictionary: ok, translation: ok, voice: ok }]))).toEqual({ ok: true, text: 'Everything for your languages is available locally.' })
  })
  it('names what is missing per language', () => {
    const r = offlineSummary(base([{ code: 'pl', name: 'Polish', dictionary: ok, translation: no, voice: no }]))
    expect(r.ok).toBe(false)
    expect(r.text).toBe('Still needed: Polish needs a translation model and a voice model.')
  })
  it('says nothing without languages', () => {
    expect(offlineSummary(base([])).text).toBe('')
  })
})
