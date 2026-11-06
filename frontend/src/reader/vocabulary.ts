
// What the words of a page say about how well you know it. "Known" is status 4, 5 and 99; "learning" 1, 2 and 3; 98 is ignored;
// "new" is a word you have not started on (status 0). Ignored words do not count towards the known share.
export const KNOWN = [4, 5, 99]
export const LEARNING = [1, 2, 3]
export const IGNORED = 98
export const WORDS_PER_MINUTE = 150

export type WordLike = { text: string; isWord: boolean; status: number; index: number; termId: number | null; sentence: number }

export type NewWord = { text: string; count: number; index: number; termId: number | null; sentence: number } // index and sentence: its first place on the page

export type PageVocabulary = {
  words: number // running words
  unique: number // different words
  known: { running: number; unique: number }
  learning: { running: number; unique: number; byStatus: Record<1 | 2 | 3, number> } // byStatus: different words at each stage
  fresh: { running: number; unique: number }
  ignored: { running: number; unique: number }
  knownPercent: number // of the words that count (not the ignored ones)
  minutes: number
  newWords: NewWord[] // the words not started on, most frequent first
}

export function pageVocabulary(items: WordLike[]): PageVocabulary {
  const kinds = { known: new Map<string, number>(), learning: new Map<string, number>(), fresh: new Map<string, number>(), ignored: new Map<string, number>() }
  const stage = new Map<string, number>()
  const first = new Map<string, WordLike>()
  let words = 0
  for (const it of items) {
    if (!it.isWord) continue
    words++
    const key = it.text.toLowerCase()
    const kind = KNOWN.includes(it.status) ? 'known' : LEARNING.includes(it.status) ? 'learning' : it.status === IGNORED ? 'ignored' : 'fresh'
    kinds[kind].set(key, (kinds[kind].get(key) ?? 0) + 1)
    if (kind === 'learning') stage.set(key, it.status)
    if (kind === 'fresh' && !first.has(key)) first.set(key, it)
  }
  const total = (m: Map<string, number>) => [...m.values()].reduce((a, b) => a + b, 0)
  const sum = (kind: keyof typeof kinds) => ({ running: total(kinds[kind]), unique: kinds[kind].size })
  const byStatus: Record<1 | 2 | 3, number> = { 1: 0, 2: 0, 3: 0 }
  for (const s of stage.values()) byStatus[s as 1 | 2 | 3]++
  const counted = words - total(kinds.ignored)
  const knownPercent = counted > 0 ? Math.round((1000 * total(kinds.known)) / counted) / 10 : 100
  const newWords = [...kinds.fresh.entries()]
    .map(([key, count]) => {
      const at = first.get(key)!
      return { text: at.text, count, index: at.index, termId: at.termId, sentence: at.sentence }
    })
    .sort((a, b) => b.count - a.count || a.index - b.index)
  return {
    words,
    unique: new Set(items.filter((i) => i.isWord).map((i) => i.text.toLowerCase())).size,
    known: sum('known'),
    learning: { ...sum('learning'), byStatus },
    fresh: sum('fresh'),
    ignored: sum('ignored'),
    knownPercent,
    minutes: Math.round(words / WORDS_PER_MINUTE),
    newWords,
  }
}

// Widths of the known / learning / new parts of a bar, in percent (ignored words are left out).
export function vocabularyBar(v: PageVocabulary): { known: number; learning: number; fresh: number } {
  const counted = v.known.running + v.learning.running + v.fresh.running
  if (counted === 0) return { known: 100, learning: 0, fresh: 0 }
  return { known: (100 * v.known.running) / counted, learning: (100 * v.learning.running) / counted, fresh: (100 * v.fresh.running) / counted }
}
