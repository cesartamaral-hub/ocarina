// The progress bar of words learned in Ocarina: the next step to work towards (or the goal you set) and how far along that is.
export const STEPS = [50, 100, 250, 500, 1000, 2000, 3000, 5000, 7500, 10000]

// The next step above `learned`; beyond the table every 5,000. A goal you set that is still ahead wins over the steps.
export function nextGoal(learned: number, custom?: number | null): number {
  if (custom && custom > learned) return custom
  const step = STEPS.find((s) => s > learned)
  return step ?? (Math.floor(learned / 5000) + 1) * 5000
}

export function progress(learned: number, custom?: number | null): { goal: number; toGo: number; fraction: number } {
  const goal = nextGoal(learned, custom)
  return { goal, toGo: goal - learned, fraction: Math.min(1, learned / goal) }
}
