// Whether the word panel asks Wiktionary by itself, once a dictionary on this Mac has answered. It sends the word over the internet, so
// it follows the setting, stays off while Work offline is on, and leaves numbers, bare punctuation and long selections to the button.
export const AUTO_WIKTIONARY = 'dictionary.autoWiktionary'
export const MAX_AUTO_WORDS = 4

export function shouldLookUpOnline({
  offline,
  enabled,
  text,
}: {
  offline: boolean
  enabled: boolean
  text: string
}): boolean {
  if (offline || !enabled) return false
  const clean = text.trim()
  if (!/\p{L}/u.test(clean)) return false // digits, punctuation
  return clean.split(/\s+/).length <= MAX_AUTO_WORDS
}
