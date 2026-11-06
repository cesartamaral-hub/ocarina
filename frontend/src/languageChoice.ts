// The first-run language picker: every language in alphabetical order behind a search, chosen ones on the other side.
export const alphabetical = (names: string[]): string[] => [...names].sort((a, b) => a.localeCompare(b))

export const matching = (names: string[], query: string): string[] => {
  const q = query.trim().toLowerCase()
  return q ? names.filter((n) => n.toLowerCase().includes(q)) : names
}

export const toggled = (chosen: string[], name: string): string[] => (chosen.includes(name) ? chosen.filter((n) => n !== name) : [...chosen, name])

// The next highlighted row after an arrow key, staying inside the list.
export const moved = (active: number, key: 'ArrowDown' | 'ArrowUp', count: number): number =>
  count === 0 ? 0 : Math.min(count - 1, Math.max(0, active + (key === 'ArrowDown' ? 1 : -1)))
