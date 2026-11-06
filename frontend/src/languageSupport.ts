import type { Feature, LanguageSupport } from './api'

// The features of a language, in the words shown in Settings → Languages, with what each state means.
export const FEATURES: { key: Exclude<keyof LanguageSupport, 'language' | 'code' | 'level'>; label: string; what: string }[] = [
  { key: 'meanings', label: 'Meanings', what: 'word meanings from local dictionaries' },
  { key: 'aiVoice', label: 'AI voice', what: 'books read aloud by an AI voice model' },
  { key: 'translation', label: 'Translation', what: 'sentence translation by a local model' },
  { key: 'audioSync', label: 'Audio sync', what: 'your own recordings following the text' },
  { key: 'macVoice', label: 'Mac voice', what: 'words said by a voice installed in macOS' },
]

const STATE: Record<Feature, string> = {
  ready: 'ready',
  download: 'not downloaded yet (Settings → Models)',
  online: 'online only: the local dictionaries do not have it',
  none: 'not available',
}

export const featureTitle = (label: string, what: string, state: Feature): string => `${label}: ${what}: ${STATE[state]}`

export const levelLabel = (level: LanguageSupport['level']): string => (level === 'full' ? 'Full support' : 'Reading and basic features')
