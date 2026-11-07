import type { AudioOptions } from './api'

export type MenuItem = {
  group: 'model' | 'voice'
  id: string
  label: string
  note?: string
}

// What the "Change" menu on the audio page lists: the installed models, then only the voices that belong with
// the chosen model (a Mac voice goes with the Mac voice, clips with the other models).
export function audioMenuItems(options: AudioOptions, modelId: string): { models: MenuItem[]; voices: MenuItem[] } {
  const models = options.models
    .filter((m) => m.installed && !m.problem)
    .map((m): MenuItem => ({
      group: 'model',
      id: m.id,
      label: m.name,
      note: m.id === options.defaultModel ? 'language default' : undefined,
    }))
  const voices = options.voices
    .filter((v) => (v.model ? v.model === modelId : modelId !== 'mac-voice'))
    .map((v): MenuItem => ({
      group: 'voice',
      id: v.id,
      label: v.name,
      note: v.id === options.defaultVoice ? 'language default' : undefined,
    }))
  return { models, voices }
}
