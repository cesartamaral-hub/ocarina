import { API, json, send } from './client'

export type PronounceSource = 'auto' | 'voice' | 'speaker' | 'google' | 'system'

export const PRONOUNCE_SOURCES: { id: PronounceSource; name: string; detail: string }[] = [
  { id: 'auto', name: 'Automatic', detail: 'The first that works: the AI voice if it is downloaded and knows the language, then the Mac system voice, then a recording by a person (online, single words). Never Google: choose that yourself.' },
  { id: 'voice', name: 'AI voice (the one that reads your books)', detail: 'The AI voice and model chosen for the language under Voices. Runs on this Mac, offline.' },
  { id: 'speaker', name: 'Recording by a person (online)', detail: 'A native speaker recording from Wiktionary, for single words that have one. Needs internet.' },
  { id: 'google', name: 'Google Translate voice (online)', detail: 'Needs internet; the text is sent to Google. An unofficial address that can stop working.' },
  { id: 'system', name: 'Mac system voice', detail: 'Instant and offline: the voice built into macOS. Not the voice that reads your books.' },
]

export type Pronounced = { url: string; source: PronounceSource; note: string | null }

export const pronounce = (text: string, languageId: number, source?: PronounceSource) =>
  send<Pronounced>('POST', `${API}/pronounce`, { text, languageId, source })

export type SystemVoices = {
  languageId: number
  language: string
  code: string | null
  chosen: string | null // the voice that would speak now
  voices: { name: string; quality: 'premium' | 'enhanced' | 'standard'; novelty: boolean }[]
}

export const getSystemVoices = () => fetch(`${API}/pronounce/system-voices`).then((r) => json<SystemVoices[]>(r))

export const previewSystemVoice = (name: string) => send<{ url: string }>('POST', `${API}/pronounce/system-voices/preview`, { name })

export const openVoiceSettings = () => send<{ ok: boolean }>('POST', `${API}/pronounce/open-voice-settings`, {})
