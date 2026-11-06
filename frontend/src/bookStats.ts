import type { Book, BookStats } from './api'

// How the book list presents a book's numbers, and how it orders them.

// The widths of the known / learning / new parts of the bar, in percent of the words that count (ignored ones do not).
export function barParts(s: BookStats): { known: number; learning: number; new: number } {
  const counted = s.known + s.learning + s.new
  if (counted === 0) return { known: 100, learning: 0, new: 0 }
  return { known: (100 * s.known) / counted, learning: (100 * s.learning) / counted, new: (100 * s.new) / counted }
}

export function duration(minutes: number): string {
  if (minutes < 1) return 'under a minute'
  if (minutes < 60) return `${minutes} min`
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return m === 0 ? `${h} h` : `${h} h ${m} min`
}

// "about 4 min", or "under a minute" for a very short text.
export const readingTime = (minutes: number): string => (minutes < 1 ? duration(minutes) : `about ${duration(minutes)}`)

export type SortKey = 'recent' | 'easiest' | 'progress' | 'title'
export const SORTS: { key: SortKey; label: string }[] = [
  { key: 'title', label: 'Title' },
  { key: 'recent', label: 'Recently read' },
  { key: 'easiest', label: 'Easiest first' },
  { key: 'progress', label: 'Furthest along' },
]

const byTitle = (a: Book, b: Book) => a.title.localeCompare(b.title)
const progress = (b: Book) => (b.pages > 0 ? (b.currentPage - 1) / b.pages : 0)

// Books never read go last when sorting by recent; books without numbers yet go last when sorting by ease.
export function sortBooks(books: Book[], key: SortKey): Book[] {
  const sorted = [...books]
  if (key === 'recent') sorted.sort((a, b) => (b.lastRead ?? '').localeCompare(a.lastRead ?? '') || byTitle(a, b))
  else if (key === 'easiest') sorted.sort((a, b) => (b.stats?.knownPercent ?? -1) - (a.stats?.knownPercent ?? -1) || byTitle(a, b))
  else if (key === 'progress') sorted.sort((a, b) => progress(b) - progress(a) || byTitle(a, b))
  else sorted.sort(byTitle)
  return sorted
}
