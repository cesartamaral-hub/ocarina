import type { DiskSpace, Model } from './api'

const covers = (m: Model, codes: string[]) => codes.length === 0 || m.languages.some((c) => codes.includes(c))

// Of the translation models that could be the starter, the one to offer: one you already have, else the one that covers the most of your
// languages (the first listed wins a tie: the catalog lists the better starter first).
export function bestTranslation(models: Model[], codes: string[]): Model | undefined {
  const candidates = models.filter((m) => m.kind === 'text' && m.starter && covers(m, codes))
  const have = candidates.filter((m) => m.installed)
  const pool = have.length > 0 ? have : candidates
  const coverage = (m: Model) => codes.filter((c) => m.languages.includes(c)).length
  return pool.reduce<Model | undefined>((best, m) => (best === undefined || coverage(m) > coverage(best) ? m : best), undefined)
}

// Which optional downloads Welcome shows (the recommended ones that list one of the languages you picked, and only one translation model:
// the one that covers your languages best) and which it ticks for you (that translation model: only when you are online and it fits in the free space).
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
