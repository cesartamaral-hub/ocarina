import { describe, expect, it } from 'vitest'
import { cardLabel, isWholeSentence, sendsTo, serviceName, targetName } from './cardWording'

describe('wording', () => {
  it('names the services and says where the text goes', () => {
    expect(serviceName('local')).toBe('Local model')
    expect(serviceName('mymemory')).toBe('MyMemory')
    expect(sendsTo('local')).toBe('Processed locally')
    expect(sendsTo('deepl')).toBe('Sent to DeepL')
  })
  it('names the target languages', () => {
    expect(targetName('en')).toBe('English')
    expect(targetName('xx')).toBe('xx')
  })
  it('labels the card with what it holds', () => {
    expect(cardLabel('sentence', 'Ik woon in Amsterdam.')).toBe('Sentence')
    expect(cardLabel('text', 'Ik woon in Amsterdam en ik werk daar.')).toBe('Selected text · 8 words')
    expect(cardLabel('text', 'Hallo')).toBe('Selected text')
  })
})

describe('isWholeSentence', () => {
  const items = [
    { sentence: 4, index: 10 },
    { sentence: 4, index: 11 },
    { sentence: 4, index: 12 },
    { sentence: 5, index: 13 },
  ]
  it('is true when the range is exactly the sentence', () => {
    expect(isWholeSentence(items, 4, [10, 12])).toBe(true)
  })
  it('is false for part of a sentence, more than one, or no range', () => {
    expect(isWholeSentence(items, 4, [10, 11])).toBe(false)
    expect(isWholeSentence(items, 4, [10, 13])).toBe(false)
    expect(isWholeSentence(items, 4, undefined)).toBe(false)
    expect(isWholeSentence(items, 9, [1, 2])).toBe(false)
  })
})
