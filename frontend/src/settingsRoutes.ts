// The settings sections, and where each lives: #/settings/<section>. The languages section has pages of its own below it.
export type SectionId = 'appearance' | 'shortcuts' | 'languages' | 'tags' | 'models' | 'voices' | 'translation' | 'backups' | 'storage'

export const SECTIONS: { id: SectionId; label: string; group: string }[] = [
  { id: 'appearance', label: 'Appearance', group: 'Reading' },
  { id: 'shortcuts', label: 'Keyboard shortcuts', group: 'Reading' },
  { id: 'languages', label: 'Languages', group: 'Languages' },
  { id: 'tags', label: 'Tags', group: 'Languages' },
  { id: 'models', label: 'Models', group: 'Audio and translation' },
  { id: 'voices', label: 'Voices', group: 'Audio and translation' },
  { id: 'translation', label: 'Translation', group: 'Audio and translation' },
  { id: 'backups', label: 'Backups', group: 'Library' },
  { id: 'storage', label: 'Storage', group: 'Library' },
]

export const GROUPS = [...new Set(SECTIONS.map((s) => s.group))]
export const DEFAULT_SECTION: SectionId = 'appearance'
export const sectionHash = (id: SectionId): string => `#/settings/${id}`
const isSection = (value: string): value is SectionId => SECTIONS.some((s) => s.id === value)

// "#/settings/languages/12" is the section "languages" with the rest "12"; null when the address is not a settings page.
export function parseSettings(hash: string): { section: SectionId; rest: string } | null {
  const m = hash.match(/^#\/settings\/([a-z]+)(?:\/(.*))?$/)
  return m && isSection(m[1]) ? { section: m[1], rest: m[2] ?? '' } : null
}

// Addresses from before the sections existed (and the bare "#/settings") go to their place; null when the address is current.
export function legacyRedirect(hash: string, lastSection: string | null = null): string | null {
  if (hash === '#/settings' || hash === '#/settings/') return sectionHash(lastSection && isSection(lastSection) ? lastSection : DEFAULT_SECTION)
  const old = hash.match(/^#\/(appearance|shortcuts|tags|translation|backups|storage|languages)(\/.*)?$/)
  if (old) return `#/settings/${old[1]}${old[2] ?? ''}`
  return null
}
