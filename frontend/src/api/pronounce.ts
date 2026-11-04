import { API, send } from './client'

export type PronounceSource = 'voice' | 'speaker' | 'google' | 'system'

export const PRONOUNCE_SOURCES: { id: PronounceSource; name: string; detail: string }[] = [
  { id: 'voice', name: 'Your voice', detail: 'The voice and model chosen for the language, the one that reads your books. On this Mac.' },
  { id: 'speaker', name: "A person's recording", detail: 'A recording from Wiktionary, for single words that have one. Needs internet.' },
  { id: 'google', name: "Google Translate's voice", detail: 'Needs internet; the text is sent to Google. An unofficial address that can stop working.' },
  { id: 'system', name: "This Mac's voice", detail: 'Instant, on this Mac. Another voice than your books.' },
]

export type Pronounced = { url: string; source: PronounceSource; note: string | null }

export const pronounce = (text: string, languageId: number, source?: PronounceSource) =>
  send<Pronounced>('POST', `${API}/pronounce`, { text, languageId, source })
