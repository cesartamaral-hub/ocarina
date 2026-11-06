import { describe, expect, it } from 'vitest'
import type { Book, BookStats } from './api'
import { barParts, duration, readingTime, sortBooks } from './bookStats'

const stats = (over: Partial<BookStats> = {}): BookStats => ({ words: 100, unique: 60, known: 50, learning: 20, ignored: 0, new: 30, newUnique: 20, knownPercent: 50, minutes: 1, ...over })
const book = (id: number, title: string, over: Partial<Book> = {}): Book => ({
  id, title, language: 'Dutch', hasAudio: false, ocarinaAudio: false, pages: 10, currentPage: 1, sourceUri: '', tags: [], archived: false, stats: null, indexing: false, lastRead: null, ...over,
})

describe('barParts', () => {
  it('adds up to 100 and leaves out ignored words', () => {
    const p = barParts(stats({ ignored: 40 }))
    expect(p.known).toBe(50)
    expect(p.known + p.learning + p.new).toBeCloseTo(100)
  })
  it('shows a book of only ignored words as known', () => {
    expect(barParts(stats({ known: 0, learning: 0, new: 0, ignored: 10 }))).toEqual({ known: 100, learning: 0, new: 0 })
  })
})

describe('duration', () => {
  it('says it in plain words', () => {
    expect(duration(0)).toBe('under a minute')
    expect(duration(28)).toBe('28 min')
    expect(duration(60)).toBe('1 h')
    expect(duration(95)).toBe('1 h 35 min')
  })
})

describe('sortBooks', () => {
  const books = [
    book(1, 'Zebra', { lastRead: '2026-11-01T10:00:00', stats: stats({ knownPercent: 80 }), currentPage: 9 }),
    book(2, 'Appel', { lastRead: '2026-11-03T10:00:00', stats: stats({ knownPercent: 97 }) }),
    book(3, 'Mango'),
  ]
  const ids = (key: Parameters<typeof sortBooks>[1]) => sortBooks(books, key).map((b) => b.id)
  it('by title', () => expect(ids('title')).toEqual([2, 3, 1]))
  it('by recently read, never-read last', () => expect(ids('recent')).toEqual([2, 1, 3]))
  it('by ease, books without numbers last', () => expect(ids('easiest')).toEqual([2, 1, 3]))
  it('by progress', () => expect(ids('progress')[0]).toBe(1))
  it('does not change the list it was given', () => {
    sortBooks(books, 'recent')
    expect(books.map((b) => b.id)).toEqual([1, 2, 3])
  })
})

describe('readingTime', () => {
  it('says "about" for a few minutes and none for a very short text', () => {
    expect(readingTime(4)).toBe('about 4 min')
    expect(readingTime(90)).toBe('about 1 h 30 min')
    expect(readingTime(0)).toBe('under a minute')
  })
})
