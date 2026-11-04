// Small rules for how the Reading page words things.

const DAY = 24 * 60 * 60 * 1000

// "today", "yesterday", "5 days ago", or the date once it is more than a month back. `today` is a local date.
export function relativeDay(iso: string | null, today: Date = new Date()): string {
  if (!iso) return 'never'
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number)
  const then = new Date(y, m - 1, d)
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate())
  const days = Math.round((start.getTime() - then.getTime()) / DAY)
  if (days <= 0) return 'today'
  if (days === 1) return 'yesterday'
  if (days <= 31) return `${days} days ago`
  return then.toLocaleDateString('en', { day: 'numeric', month: 'short', year: then.getFullYear() === start.getFullYear() ? undefined : 'numeric' })
}

// Which languages the page shows: all of them, or the one chosen (all of them again if the chosen one is gone).
export function visibleLanguages<T extends { id: number }>(languages: T[], choice: string): T[] {
  if (choice === 'all') return languages
  const one = languages.filter((l) => String(l.id) === choice)
  return one.length > 0 ? one : languages
}

// Points for a line chart of known words over time; a day with no change keeps the line level.
export function growthPoints(growth: { date: string; known: number }[]): { label: string; value: number }[] {
  if (growth.length === 0) return []
  const points = [{ label: growth[0].date, value: 0 }]
  for (const g of growth) points.push({ label: g.date, value: g.known })
  return points
}
