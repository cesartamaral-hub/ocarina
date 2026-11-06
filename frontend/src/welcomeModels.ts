import type { DiskSpace, Model } from './api'

const USABLE = ['A', 'B', 'C', 'D']
const covers = (m: Model, codes: string[]) => codes.length === 0 || m.languages.some((c) => codes.includes(c))

// The average score a translation model measured over your languages (the ones it was graded A to D in); -1 when it has none of them.
export function meanScore(m: Model, codes: string[]): number {
  const rows = codes.map((c) => m.quality?.[c]).filter((r) => r && r.grade && USABLE.includes(r.grade))
  return rows.length ? rows.reduce((n, r) => n + r!.chrf, 0) / rows.length : -1
}

// Of the translation models that could be the starter, the one to offer: one you already have, else the best on average for your languages.
export function bestTranslation(models: Model[], codes: string[]): Model | undefined {
  const candidates = models.filter((m) => m.kind === 'text' && m.starter && covers(m, codes))
  const have = candidates.filter((m) => m.installed)
  const pool = have.length > 0 ? have : candidates
  return pool.reduce<Model | undefined>((best, m) => (best === undefined || meanScore(m, codes) > meanScore(best, codes) ? m : best), undefined)
}

// Which optional downloads Welcome shows (the recommended ones that list one of the languages you picked, and only one translation model:
// the best for your languages) and which it ticks for you (that translation model: only when you are online and it fits in the free space).
export function relevantModels(models: Model[], codes: string[]): Model[] {
  const best = bestTranslation(models, codes)
  return models
    .filter((m) => m.badge === 'Recommended' && covers(m, codes) && (m.kind !== 'text' || m.id === best?.id))
    .map((m) => ({ ...m, starter: m.kind === 'text' ? m.id === best?.id : m.starter }))
    .sort((a, b) => Number(Boolean(b.starter)) - Number(Boolean(a.starter))) // the recommended one first
}

export const sizeOf = (list: Model[]): number => list.reduce((n, m) => n + m.sizeBytes, 0)

export const fitsInSpace = (list: Model[], space: DiskSpace | null): boolean => !space || sizeOf(list) + space.queuedBytes + space.marginBytes <= space.freeBytes

export function autoTicked(todo: Model[], online: boolean, space: DiskSpace | null): string[] {
  const starters = todo.filter((m) => m.starter && !m.installed)
  return online && fitsInSpace(starters, space) ? starters.map((m) => m.id) : []
}
