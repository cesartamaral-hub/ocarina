import { getPref, setPref } from './api'

// Theme, reading text size and reading font. They are preferences (saved on the server) and are applied to
// the page as an attribute and two CSS variables.
export type Theme = 'system' | 'light' | 'dark'
export type ReaderFont = 'sans' | 'serif'

export const SIZE_RANGE = { min: 14, max: 32, standard: 18 }
const FONTS: Record<ReaderFont, string> = {
  sans: "-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif",
  serif: "'New York', 'Iowan Old Style', Georgia, 'Times New Roman', serif",
}

export const appearance = () => ({
  theme: getPref<Theme>('theme', 'system'),
  size: getPref<number>('readerSize', SIZE_RANGE.standard),
  font: getPref<ReaderFont>('readerFont', 'sans'),
})

export function applyAppearance(): void {
  const { theme, size, font } = appearance()
  const root = document.documentElement
  if (theme === 'system') root.removeAttribute('data-theme')
  else root.setAttribute('data-theme', theme)
  root.style.setProperty('--reader-size', `${size}px`)
  root.style.setProperty('--reader-font', FONTS[font])
}

export function saveAppearance(change: Partial<{ theme: Theme; size: number; font: ReaderFont }>): void {
  if (change.theme !== undefined) setPref('theme', change.theme)
  if (change.size !== undefined) setPref('readerSize', change.size)
  if (change.font !== undefined) setPref('readerFont', change.font)
  applyAppearance()
}
