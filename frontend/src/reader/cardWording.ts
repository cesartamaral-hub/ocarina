import { wordCount } from './editing'

const SERVICES: Record<string, string> = { local: 'Local model', mymemory: 'MyMemory', deepl: 'DeepL' }
export const serviceName = (provider: string): string => SERVICES[provider] ?? provider

// Where a sentence goes when it is translated: the privacy line under the Translate button.
export const sendsTo = (provider: string): string => (provider === 'local' ? 'Processed locally' : `Sent to ${serviceName(provider)}`)

export const TARGET_NAMES: Record<string, string> = { en: 'English', nl: 'Dutch', fr: 'French', de: 'German', es: 'Spanish', it: 'Italian', pt: 'Portuguese', pl: 'Polish' }
export const targetName = (code: string): string => TARGET_NAMES[code] ?? code

// The small heading of the card: what it holds, and for a longer text how long it is.
export function cardLabel(kind: 'sentence' | 'text', text: string): string {
  if (kind === 'sentence') return 'Sentence'
  const n = wordCount(text)
  return n > 1 ? `Selected text · ${n} words` : 'Selected text'
}

// Whether a picked range is exactly one sentence of the page (so the book's own translation of it applies).
export function isWholeSentence(items: { sentence: number; index: number }[], sentence: number, span: [number, number] | undefined): boolean {
  if (!span) return false
  const own = items.filter((i) => i.sentence === sentence)
  return own.length > 0 && own[0].index === span[0] && own[own.length - 1].index === span[1]
}
