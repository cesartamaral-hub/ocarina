import type { TranslateSettings } from './api'

// A text this long or shorter is translated when it is added unless you say otherwise; a longer one is left for the reader, page by page.
export const LONG_TEXT_WORDS = 1200

export const wordCount = (text: string): number => (text.trim() ? text.trim().split(/\s+/).length : 0)

export const isLong = (text: string): boolean => wordCount(text) > LONG_TEXT_WORDS

export type Choice = { key: string; name: string; provider: string; model: string | null }

// The ways the text can be translated now: each model on this Mac, and the online services that can be used (DeepL needs its key).
export function translateChoices(s: TranslateSettings): { choices: Choice[]; fallback: string } {
  const choices: Choice[] = []
  for (const m of s.localModels) if (m.installed) choices.push({ key: `local:${m.id}`, name: `${m.name.replace(/\s*\(.*\)\s*$/, '')} · on this Mac`, provider: 'local', model: m.id })
  for (const p of s.providers) {
    if (p.id === 'local') continue
    if (p.needsKey && !(p.id === 'deepl' && s.hasDeeplKey)) continue
    choices.push({ key: p.id, name: p.name, provider: p.id, model: null })
  }
  // The one set under Translation, when it can be used; else the first.
  const wanted = s.provider === 'local' ? `local:${s.localModel.id}` : s.provider
  return { choices, fallback: choices.some((c) => c.key === wanted) ? wanted : (choices[0]?.key ?? '') }
}
