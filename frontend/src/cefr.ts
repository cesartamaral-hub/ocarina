// A guide to how far a vocabulary has come on the CEFR scale. The figures are the usual frequency-based estimates: they vary by study and by
// whether vocabulary is active or passive, so this is a guide and not a test.

export type Level = { id: string; words: number; range: string; name: string; blurb: string }

export const LEVELS: Level[] = [
  { id: 'A1', words: 500, range: '500 to 1,000', name: 'Beginner', blurb: 'Greetings, basic needs and simple set phrases.' },
  { id: 'A2', words: 1200, range: '1,000 to 2,000', name: 'Pre-intermediate', blurb: 'Everyday topics, shopping, simple past and future.' },
  { id: 'B1', words: 2500, range: '2,500 to 3,000', name: 'Intermediate', blurb: 'Independent travel, stating opinions, following the gist of media.' },
  { id: 'B2', words: 4000, range: '4,000 to 5,000', name: 'Upper-intermediate', blurb: 'Following news and films, holding real conversations, working in the language.' },
  { id: 'C1', words: 8000, range: 'about 8,000', name: 'Advanced', blurb: 'Nuance, idioms, professional or academic use.' },
  { id: 'C2', words: 16000, range: '10,000 to over 16,000', name: 'Mastery', blurb: 'Subtle register, humour and specialised vocabulary.' },
]

export type Progress = {
  level: Level | null // the highest level reached; null below A1 (A0)
  label: string // "A0", "A2", ...
  next: Level | null // the level being worked towards; null once C2 is reached
  toNext: number // words still needed for it
  fraction: number // how far through the stretch towards `next` (0 to 1)
  segments: number[] // for each level, how full its stretch is (0 to 1): the stretch of a level is the words from the one before it
}

// Where a number of known words stands. The stretch towards a level begins where the previous level's words end.
export function progressFor(known: number): Progress {
  const words = Math.max(0, Math.floor(known))
  const segments = LEVELS.map((l, i) => {
    const from = i === 0 ? 0 : LEVELS[i - 1].words
    return Math.min(1, Math.max(0, (words - from) / (l.words - from)))
  })
  const reached = LEVELS.filter((l) => words >= l.words)
  const level = reached.length ? reached[reached.length - 1] : null
  const next = LEVELS[reached.length] ?? null
  const from = level ? level.words : 0
  return {
    level,
    label: level ? level.id : 'A0',
    next,
    toNext: next ? next.words - words : 0,
    fraction: next ? (words - from) / (next.words - from) : 1,
    segments,
  }
}
