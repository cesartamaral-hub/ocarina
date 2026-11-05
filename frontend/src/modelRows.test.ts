import { describe, expect, it } from 'vitest'
import type { Model } from './api'
import { gradeLevel, speechCodesUsing, speechModelFor, speedLevel } from './modelRows'

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

describe('gradeLevel', () => {
  it('groups the letters', () => {
    expect(['A', 'A-', 'B+', 'B', 'C+', undefined].map(gradeLevel)).toEqual(['top', 'top', 'good', 'good', 'fair', 'none'])
  })
})
