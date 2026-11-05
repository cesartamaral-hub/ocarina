import { codeOfLanguage } from './speechLanguages'

// Helpers for the Vocabulary page.

// Words with a status you set: the five levels and "well known". Ignored words (98) are left out unless their chip is on.
export const CHIPS: { status: number; label: string; title: string }[] = [
  { status: 1, label: '1', title: 'New' },
  { status: 2, label: '2', title: 'Recognised' },
  { status: 3, label: '3', title: 'Familiar' },
  { status: 4, label: '4', title: 'Learned' },
  { status: 5, label: '5', title: 'Known' },
  { status: 99, label: '✓', title: 'Well known' },
  { status: 98, label: '✕', title: 'Ignored' },
]
export const DEFAULT_STATUSES = [1, 2, 3, 4, 5, 99]

// "NL", "PL": the code of a language Ocarina knows, else the first two letters of its name.
export const languageAbbr = (name: string): string => (codeOfLanguage(name) ?? name.trim().slice(0, 2)).toUpperCase()

export type Part = { text: string; bold: boolean }

const escapeRegExp = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

// The sentence in parts, with the word (or phrase) marked wherever it is, ignoring case.
export function contextParts(sentence: string, word: string): Part[] {
  const w = word.replace(/​/g, '').trim()
  if (!w) return [{ text: sentence, bold: false }]
  const re = new RegExp(`(?<![\\p{L}\\p{N}])(${escapeRegExp(w).replace(/\s+/g, '\\s+')})(?![\\p{L}\\p{N}])`, 'giu')
  const parts: Part[] = []
  let last = 0
  for (const m of sentence.matchAll(re)) {
    if (m.index > last) parts.push({ text: sentence.slice(last, m.index), bold: false })
    parts.push({ text: m[0], bold: true })
    last = m.index + m[0].length
  }
  if (last < sentence.length) parts.push({ text: sentence.slice(last), bold: false })
  return parts.length ? parts : [{ text: sentence, bold: false }]
}

// "today", "yesterday", "5 days ago", "3 weeks ago", "2 months ago", "a year ago".
export function timeAgo(created: string | null | undefined, now = new Date()): string {
  if (!created) return ''
  const then = new Date(created.replace(' ', 'T'))
  if (Number.isNaN(then.getTime())) return ''
  const days = Math.floor((now.getTime() - then.getTime()) / 86_400_000)
  if (days < 1) return 'today'
  if (days === 1) return 'yesterday'
  if (days < 14) return `${days} days ago`
  if (days < 60) return `${Math.floor(days / 7)} weeks ago`
  if (days < 365) return `${Math.floor(days / 30)} months ago`
  const years = Math.floor(days / 365)
  return years === 1 ? 'a year ago' : `${years} years ago`
}

// Where an arrow key (or Home or End) takes the active row: the id of the next one, or null when there is nothing to move to.
export function moveActive(ids: number[], current: number | null, key: string): number | null {
  if (ids.length === 0) return null
  const i = current === null ? -1 : ids.indexOf(current)
  if (key === 'Home') return ids[0]
  if (key === 'End') return ids[ids.length - 1]
  if (key === 'ArrowDown') return ids[Math.min(i + 1, ids.length - 1)]
  if (key === 'ArrowUp') return ids[i <= 0 ? 0 : i - 1]
  return null
}
