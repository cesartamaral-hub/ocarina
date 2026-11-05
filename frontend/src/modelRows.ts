import type { Model } from './api'

// What the model rows show, worked out from the model list (see ModelList.tsx).

// Four bars. A model that has been tried here is rated by how long it took; before that, by the catalog's own rating.
export function speedLevel(m: Pick<Model, 'kind' | 'speed' | 'check' | 'benchmark'>): number {
  const kind = m.kind ?? 'speech'
  const perAudio = m.check?.ok ? m.check.secondsPerSecondOfAudio : m.benchmark?.secondsPerSecondOfAudio
  const perSentence = m.check?.ok ? m.check.secondsPerSentence : m.benchmark?.secondsPerSentence
  if (kind === 'speech' && perAudio != null) return perAudio < 0.3 ? 4 : perAudio < 0.8 ? 3 : perAudio < 1.5 ? 2 : 1
  if (kind === 'text' && perSentence != null) return perSentence < 1 ? 4 : perSentence < 3 ? 3 : perSentence < 8 ? 2 : 1
  return Math.min(4, Math.max(1, m.speed ?? 2))
}

// The model that makes the audio for a language: the one chosen for it if it is installed, else the first installed that speaks it.
export function speechModelFor(code: string, models: Model[], chosenId: string): Model | undefined {
  const usable = models.filter((m) => (m.kind ?? 'speech') === 'speech' && m.installed && !(m.check && !m.check.ok) && m.languages.includes(code))
  return usable.find((m) => m.id === chosenId) ?? usable[0]
}

// The language codes a model is used for, among the codes shown.
export const speechCodesUsing = (m: Model, codes: string[], models: Model[], chosen: (code: string) => string): string[] =>
  codes.filter((code) => speechModelFor(code, models, chosen(code))?.id === m.id)

export const gradeLevel = (grade: string | undefined): 'top' | 'good' | 'fair' | 'none' => {
  if (!grade) return 'none'
  return grade.startsWith('A') ? 'top' : grade.startsWith('B') ? 'good' : 'fair'
}
