import { API, json } from './client'
import type { BookStats } from './books'

export type ReadCounts = { day: number; week: number; month: number; year: number; total: number }
export type ChartPoint = { readdate: string; wordcount: number; runningTotal: number }

export type LanguageBook = {
  id: number
  title: string
  archived: boolean
  hasAudio: boolean
  pages: number
  currentPage: number
  lastRead: string | null
  stats: BookStats | null
}

// One language you use: what you know, what your texts hold, what you have read.
export type LanguageStats = {
  id: number
  name: string
  books: { count: number; archived: number; withAudio: number; list: LanguageBook[] }
  terms: { known: number; learning: number; ignored: number; unstarted: number; vocabulary: number; phrases: number; byStatus: Record<string, number> }
  coverage: { words: number; known: number; learning: number; ignored: number; new: number; newUnique: number; knownPercent: number | null; minutesLeft: number; pendingBooks: number }
  read: ReadCounts
  streak: number
  firstRead: string | null
  lastRead: string | null
  growth: { date: string; known: number }[]
  chart: ChartPoint[]
}

export type Stats = {
  streak: number
  table: { name: string; counts: ReadCounts }[]
  chart: Record<string, ChartPoint[]>
  languages: LanguageStats[]
  totals: { readWeek: number; readToday: number; known: number; learning: number; books: number }
}

export const getStats = () => fetch(`${API}/stats`).then((r) => json<Stats>(r))
