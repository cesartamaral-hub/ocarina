import { getPref, setPref } from './api'
import { DEFAULTS, fromPreferences, normalize, toCssVars, type Typography } from './typography'

// Theme, reading text size and reading font. They are preferences (saved on the server) and are applied to
// the page as an attribute and two CSS variables.
export type Theme = 'system' | 'light' | 'dark'

// Changes apply at once; saving waits until you stop moving a slider.
let latest: Typography | null = null
let saveTimer: number | undefined
export const typography = (): Typography => latest ?? fromPreferences(getPref)

export const appearance = () => ({ theme: getPref<Theme>('theme', 'system') })

export function applyAppearance(): void {
  const root = document.documentElement
  const theme = appearance().theme
  if (theme === 'system') root.removeAttribute('data-theme')
  else root.setAttribute('data-theme', theme)
  for (const [name, value] of Object.entries(toCssVars(typography()))) root.style.setProperty(name, value)
}

export function saveAppearance(change: { theme?: Theme }): void {
  if (change.theme !== undefined) setPref('theme', change.theme)
  applyAppearance()
}

export function saveTypography(change: Partial<Typography> | 'reset'): Typography {
  const next = change === 'reset' ? DEFAULTS : normalize({ ...typography(), ...change })
  latest = next
  applyAppearance()
  window.clearTimeout(saveTimer)
  saveTimer = window.setTimeout(() => {
    setPref('reader.typography', next)
    latest = null
  }, 250)
  return next
}
