import { describe, expect, it } from 'vitest'
import type { DiskSpace, Model } from './api'
import { autoTicked, fitsInSpace, relevantModels } from './welcomeModels'

const model = (id: string, languages: string[], extra: Partial<Model> = {}): Model =>
  ({ id, name: id, description: '', license: '', languages, installed: false, sizeBytes: 1e9, downloadJob: null, badge: 'Recommended', ...extra }) as Model
const space = (free: number): DiskSpace => ({ freeBytes: free, marginBytes: 2e9, queuedBytes: 0 })

describe('the translation model Welcome offers', () => {
  const gemma = model('gemma', ['nl', 'pt', 'ru', 'ar'], { starter: true, kind: 'text' })
  const qwen = model('qwen', ['nl', 'pt', 'ru'], { starter: true, kind: 'text' })
  it('offers the one that covers more of your languages, and only one', () => {
    expect(relevantModels([qwen, gemma], ['nl', 'ar']).map((m) => m.id)).toEqual(['gemma'])
    expect(relevantModels([qwen, gemma], ['pt', 'ru']).map((m) => m.id)).toEqual(['qwen']) // the first listed wins a tie
  })
  it('keeps the one you already have', () => {
    expect(relevantModels([gemma, { ...qwen, installed: true }], ['pt']).map((m) => m.id)).toEqual(['qwen'])
  })
  it('marks only the chosen translation model as the starter', () => {
    expect(relevantModels([gemma, qwen], ['nl']).every((m) => m.starter)).toBe(true)
  })
})

describe('welcomeModels', () => {
  const translation = model('qwen', ['nl', 'pl', 'fr'], { starter: true, kind: 'text' })
  const whisper = model('whisper', ['nl', 'it', 'pt'], { kind: 'transcriber' })
  it('shows only the models that list one of your languages', () => {
    expect(relevantModels([translation, whisper], ['it']).map((m) => m.id)).toEqual(['whisper'])
    expect(relevantModels([translation, whisper], ['nl']).map((m) => m.id)).toEqual(['qwen', 'whisper'])
    expect(relevantModels([translation, model('x', [], { badge: undefined })], [])).toEqual([translation])
  })
  it('ticks the translation model when you are online and it fits', () => {
    expect(autoTicked([translation, whisper], true, space(10e9))).toEqual(['qwen'])
  })
  it('ticks nothing offline, when there is no space, or when it is installed already', () => {
    expect(autoTicked([translation], false, space(10e9))).toEqual([])
    expect(autoTicked([translation], true, space(2.5e9))).toEqual([])
    expect(autoTicked([{ ...translation, installed: true }], true, space(10e9))).toEqual([])
  })
  it('counts the margin and what is already queued', () => {
    expect(fitsInSpace([translation], space(3e9))).toBe(true)
    expect(fitsInSpace([translation], { ...space(3e9), queuedBytes: 1e9 })).toBe(false)
  })
})
