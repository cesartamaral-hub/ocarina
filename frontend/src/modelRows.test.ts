import { describe, expect, it } from 'vitest'
import type { Model } from './api'
import { coverageNote, languageCount, speechCodesUsing, speechModelFor, speedLevel } from './modelRows'

const model = (id: string, extra: Partial<Model> = {}): Model =>
  ({ id, name: id, description: '', license: 'mit', languages: ['nl', 'pl'], installed: true, kind: 'speech', sizeBytes: 1, downloadJob: null, ...extra }) as Model

describe('speedLevel', () => {
  it('uses the catalog rating until the model has been tried', () => {
    expect(speedLevel(model('a', { speed: 3 }))).toBe(3)
    expect(speedLevel(model('a'))).toBe(2)
    expect(speedLevel(model('a', { speed: 9 }))).toBe(4)
  })
  it('rates a voice by seconds per second of audio, once measured', () => {
    expect(speedLevel(model('a', { speed: 1, check: { ok: true, secondsPerSecondOfAudio: 0.2, at: 0 } }))).toBe(4)
    expect(speedLevel(model('a', { check: { ok: true, secondsPerSecondOfAudio: 0.54, at: 0 } }))).toBe(3)
    expect(speedLevel(model('a', { check: { ok: true, secondsPerSecondOfAudio: 2, at: 0 } }))).toBe(1)
  })
  it('rates a translation model by seconds per sentence', () => {
    expect(speedLevel(model('t', { kind: 'text', check: { ok: true, secondsPerSentence: 5, at: 0 } }))).toBe(2)
  })
})

describe('which voice model is used', () => {
  const a = model('a')
  const b = model('b')
  const models = [a, b, model('c', { installed: false })]
  it('is the chosen one, else the first installed', () => {
    expect(speechModelFor('nl', models, '')?.id).toBe('a')
    expect(speechModelFor('nl', models, 'b')?.id).toBe('b')
    expect(speechModelFor('nl', models, 'c')?.id).toBe('a') // not installed: ignored
    expect(speechModelFor('fr', models, '')).toBeUndefined() // nothing speaks it
  })
  it('says for which of your languages a model is used', () => {
    const chosen = (code: string) => (code === 'pl' ? 'b' : '')
    expect(speechCodesUsing(a, ['nl', 'pl'], models, chosen)).toEqual(['nl'])
    expect(speechCodesUsing(b, ['nl', 'pl'], models, chosen)).toEqual(['pl'])
  })
})

describe('the Mac voice as an engine', () => {
  const mac = model('mac', { builtin: true, languages: [] })
  it('speaks any language, and comes after a downloaded voice model', () => {
    expect(speechModelFor('it', [model('a'), mac], '')?.id).toBe('mac')
    expect(speechModelFor('nl', [model('a'), mac], '')?.id).toBe('a')
    expect(speechModelFor('nl', [model('a'), mac], 'mac')?.id).toBe('mac')
  })
})

describe('coverageNote', () => {
  const name = (c: string) => ({ nl: 'Dutch', pl: 'Polish' })[c] ?? c
  it('says nothing when the model covers your languages', () => {
    expect(coverageNote({ languages: ['nl', 'pl'] }, ['nl', 'pl'], name)).toBeNull()
    expect(coverageNote({ languages: [] }, [], name)).toBeNull()
  })
  it('names the languages it leaves out', () => {
    expect(coverageNote({ languages: ['nl'] }, ['nl', 'pl'], name)).toBe("Doesn't cover Polish")
    expect(coverageNote({ languages: ['fr'] }, ['nl', 'pl'], name)).toBe("Doesn't cover your languages")
    expect(coverageNote({ languages: ['fr'] }, ['pl'], name)).toBe("Doesn't cover Polish")
  })
})

describe('languageCount', () => {
  const name = (c: string) => c.toUpperCase()
  it('lists a few, counts many', () => {
    expect(languageCount({ languages: ['nl', 'pl'] }, name)).toBe('NL, PL')
    expect(languageCount({ languages: ['a', 'b', 'c', 'd'] }, name)).toBe('4 languages')
  })
})
