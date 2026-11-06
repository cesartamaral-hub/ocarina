import { describe, expect, it } from 'vitest'
import { FEATURES, featureTitle, levelLabel } from './languageSupport'

describe('languageSupport', () => {
  it('names the five features', () => {
    expect(FEATURES.map((f) => f.key)).toEqual(['meanings', 'aiVoice', 'translation', 'audioSync', 'macVoice'])
  })
  it('explains each state in words', () => {
    expect(featureTitle('AI voice', 'books read aloud', 'download')).toContain('not downloaded yet')
    expect(featureTitle('Meanings', 'meanings', 'online')).toContain('online only')
  })
  it('labels the level', () => {
    expect(levelLabel('full')).toBe('Full support')
    expect(levelLabel('basic')).toBe('Reading and basic features')
  })
})
