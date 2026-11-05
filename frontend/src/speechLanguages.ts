// Languages Ocarina can speak (the codes the voice model uses).
export const SPEECH_LANGUAGES: Record<string, string> = { nl: 'Dutch', pl: 'Polish', fr: 'French' }

// The code of one of those languages from the name it has in the library (Lute names some of them in their own language).
export function codeOfLanguage(name: string): string | null {
  const names: Record<string, string> = { dutch: 'nl', nederlands: 'nl', polish: 'pl', polski: 'pl', french: 'fr', français: 'fr', francais: 'fr' }
  return names[name.trim().toLowerCase()] ?? null
}
