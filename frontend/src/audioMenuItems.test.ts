import { describe, expect, it } from 'vitest'
import type { AudioOptions } from './api'
import { audioMenuItems } from './audioMenuItems'

const options: AudioOptions = {
  language: 'nl',
  defaultModel: 'mac-voice',
  defaultVoice: 'mac:Xander',
  models: [
    { id: 'mac-voice', name: 'Mac voice', installed: true, custom: false, secondsPerSecondOfAudio: 1 },
    { id: 'chatterbox', name: 'Chatterbox', installed: true, custom: false, secondsPerSecondOfAudio: 1 },
    { id: 'audio8', name: 'Audio8', installed: false, custom: false, secondsPerSecondOfAudio: 1 },
  ],
  voices: [
    { id: 'mac:Xander', name: 'Xander', builtin: true, model: 'mac-voice' },
    { id: 'dutch-sample', name: 'Dutch sample', builtin: true },
  ],
}

describe('audioMenuItems', () => {
  it('lists only the Mac voices with the Mac voice, without throwing on the clips', () => {
    const { models, voices } = audioMenuItems(options, 'mac-voice')
    expect(models.map((m) => m.id)).toEqual(['mac-voice', 'chatterbox'])
    expect(voices.map((v) => v.id)).toEqual(['mac:Xander'])
  })
  it('lists only the clips with another model', () => {
    expect(audioMenuItems(options, 'chatterbox').voices.map((v) => v.id)).toEqual(['dutch-sample'])
  })
})
