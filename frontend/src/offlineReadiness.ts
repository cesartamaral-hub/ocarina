import type { Readiness } from './api'

const LABELS = { dictionary: 'a dictionary', translation: 'a translation model', voice: 'a voice model' } as const

// One line for the Work offline setting: is everything for your languages on this Mac? Lists what is missing, language by language.
export function offlineSummary(ready: Readiness): { ok: boolean; text: string } {
  const gaps = ready.languages
    .map((l) => ({ name: l.name, missing: (Object.keys(LABELS) as (keyof typeof LABELS)[]).filter((k) => !l[k].ok).map((k) => LABELS[k]) }))
    .filter((g) => g.missing.length > 0)
  if (ready.languages.length === 0) return { ok: true, text: '' }
  if (gaps.length === 0) return { ok: true, text: 'Everything for your languages is on this Mac.' }
  return { ok: false, text: `Still needed: ${gaps.map((g) => `${g.name} needs ${g.missing.join(' and ')}`).join('; ')}.` }
}
