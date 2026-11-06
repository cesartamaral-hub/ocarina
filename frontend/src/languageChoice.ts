// The first-run language picker: the most studied languages first, the rest behind a search.
export const POPULAR = ['English', 'Spanish', 'French', 'German', 'Italian', 'Japanese', 'Mandarin Chinese', 'Portuguese', 'Russian', 'Dutch', 'Polish', 'Turkish']

// The popular languages that can still be added (in the order above), and all the others, alphabetically.
export function splitLanguages(available: string[]): { popular: string[]; rest: string[] } {
  const popular = POPULAR.filter((n) => available.includes(n))
  const rest = available.filter((n) => !popular.includes(n)).sort((a, b) => a.localeCompare(b))
  return { popular, rest }
}

export const matching = (names: string[], query: string): string[] => {
  const q = query.trim().toLowerCase()
  return q ? names.filter((n) => n.toLowerCase().includes(q)) : names
}

export const toggled = (chosen: string[], name: string): string[] => (chosen.includes(name) ? chosen.filter((n) => n !== name) : [...chosen, name])
