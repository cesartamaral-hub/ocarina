import { describe, expect, it } from 'vitest'
import type { TranslateSettings } from './api'
import { isLong, translateChoices, wordCount } from './newMaterial'

describe('how long a text is', () => {
  it('counts words and calls more than 1,200 long', () => {
    expect(wordCount('  een twee\ndrie ')).toBe(3)
    expect(wordCount('')).toBe(0)
    expect(isLong('woord '.repeat(1200))).toBe(false)
    expect(isLong('woord '.repeat(1201))).toBe(true)
  })
})

const settings = (extra: Partial<TranslateSettings> = {}): TranslateSettings =>
  ({
    provider: 'local',
    target: 'en',
    email: '',
    hasDeeplKey: false,
    deeplKeyHint: null,
    providers: [
      { id: 'mymemory', name: 'MyMemory', needsKey: false, description: '' },
      { id: 'deepl', name: 'DeepL', needsKey: true, description: '' },
      { id: 'local', name: 'On this Mac', needsKey: false, description: '' },
    ],
    localModel: { id: 'q4', name: 'Qwen3 4B (translation, MLX)', description: '', installed: true, sizeBytes: 1 },
    localModels: [
      { id: 'q4', name: 'Qwen3 4B (translation, MLX)', description: '', installed: true, sizeBytes: 1 },
      { id: 'q8', name: 'Qwen3 8B (translation, MLX)', description: '', installed: false, sizeBytes: 1 },
    ],
    targets: [],
    ...extra,
  }) as TranslateSettings

describe('translateChoices', () => {
  it('lists the models that are downloaded and the services that can be used', () => {
    const { choices, fallback } = translateChoices(settings())
    expect(choices.map((c) => c.key)).toEqual(['local:q4', 'mymemory'])
    expect(choices[0].name).toBe('Qwen3 4B · on this Mac')
    expect(fallback).toBe('local:q4')
  })
  it('offers DeepL once it has a key', () => {
    expect(translateChoices(settings({ hasDeeplKey: true })).choices.map((c) => c.key)).toContain('deepl')
  })
  it('starts with the service set under Translation', () => {
    expect(translateChoices(settings({ provider: 'mymemory' })).fallback).toBe('mymemory')
  })
  it('falls back to the first when the set one cannot be used', () => {
    const s = settings({ provider: 'deepl' })
    expect(translateChoices(s).fallback).toBe('local:q4')
  })
})
