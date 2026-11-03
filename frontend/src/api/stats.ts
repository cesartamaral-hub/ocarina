import { API, json } from './client'

export type ReadCounts = { day: number; week: number; month: number; year: number; total: number }
export type ChartPoint = { readdate: string; wordcount: number; runningTotal: number }
export type Stats = { streak: number; table: { name: string; counts: ReadCounts }[]; chart: Record<string, ChartPoint[]> }

export const getStats = () => fetch(`${API}/stats`).then((r) => json<Stats>(r))
