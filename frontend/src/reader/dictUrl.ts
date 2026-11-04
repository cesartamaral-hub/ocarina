import type { Dictionary } from '../api'

// Dictionary urls contain [LUTE] (older ones ###) where the word goes; a leading * only marked
// "open as popup" in Lute.
export function dictUrl(d: Dictionary, text: string): string {
  const word = encodeURIComponent(text)
  return d.url.replace(/^\*/, '').replace('[LUTE]', word).replace('###', word)
}
