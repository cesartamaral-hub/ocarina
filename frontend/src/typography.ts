// How the reader's text looks: size, font, weight, line length, spacing and alignment.
// This file is only the rules (defaults, limits, what the page gets); saving and applying are in appearanceSettings.ts.

export type FontKey = 'sans' | 'serif' | 'rounded' | 'mono'
export type Align = 'start' | 'center' | 'end' | 'justify'

export type Typography = {
  size: number // text size in px
  font: FontKey
  weight: number // 300, 400, 500 or 700
  width: number // line length in characters
  line: number // line height, as a multiple of the text size
  letter: number // extra space between letters, in em
  word: number // extra space between words, in em
  align: Align
}

export const DEFAULTS: Typography = { size: 18, font: 'sans', weight: 400, width: 70, line: 2, letter: 0, word: 0, align: 'start' }

type Limit = { min: number; max: number; step: number }
export const LIMITS: Record<'size' | 'width' | 'line' | 'letter' | 'word', Limit> = {
  size: { min: 14, max: 36, step: 1 },
  width: { min: 40, max: 120, step: 5 },
  line: { min: 1.4, max: 2.8, step: 0.1 },
  letter: { min: 0, max: 0.12, step: 0.01 },
  word: { min: 0, max: 0.5, step: 0.05 },
}

export const FONTS: Record<FontKey, { label: string; stack: string; charWidth: number }> = {
  sans: { label: 'Sans-serif', stack: "-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif", charWidth: 0.52 },
  serif: { label: 'Serif', stack: "'New York', 'Iowan Old Style', Georgia, 'Times New Roman', serif", charWidth: 0.5 },
  rounded: { label: 'Rounded', stack: "ui-rounded, 'SF Pro Rounded', system-ui, sans-serif", charWidth: 0.54 },
  mono: { label: 'Monospace', stack: "ui-monospace, 'SF Mono', Menlo, Consolas, monospace", charWidth: 0.6 },
}
export const WEIGHTS: { value: number; label: string }[] = [
  { value: 300, label: 'Light' },
  { value: 400, label: 'Regular' },
  { value: 500, label: 'Medium' },
  { value: 700, label: 'Bold' },
]
export const ALIGNMENTS: { value: Align; label: string }[] = [
  { value: 'start', label: 'Align to the start' },
  { value: 'center', label: 'Center' },
  { value: 'end', label: 'Align to the end' },
  { value: 'justify', label: 'Justify' },
]

const clamp = (n: number, { min, max, step }: Limit): number => {
  const snapped = Math.round(n / step) * step
  return Math.round(Math.min(Math.max(snapped, min), max) * 1000) / 1000 // no 0.30000000000000004
}
const number = (v: unknown, fallback: number, limit: Limit): number => (typeof v === 'number' && Number.isFinite(v) ? clamp(v, limit) : fallback)

// Turns whatever was saved (possibly damaged, partial or from an older version) into valid settings.
export function normalize(raw: unknown): Typography {
  const r = (typeof raw === 'object' && raw !== null ? raw : {}) as Record<string, unknown>
  return {
    size: number(r.size, DEFAULTS.size, LIMITS.size),
    font: typeof r.font === 'string' && r.font in FONTS ? (r.font as FontKey) : DEFAULTS.font,
    weight: WEIGHTS.some((w) => w.value === r.weight) ? (r.weight as number) : DEFAULTS.weight,
    width: number(r.width, DEFAULTS.width, LIMITS.width),
    line: number(r.line, DEFAULTS.line, LIMITS.line),
    letter: number(r.letter, DEFAULTS.letter, LIMITS.letter),
    word: number(r.word, DEFAULTS.word, LIMITS.word),
    align: ALIGNMENTS.some((a) => a.value === r.align) ? (r.align as Align) : DEFAULTS.align,
  }
}

// The two settings of earlier versions (text size, and sans or serif) are used until the new settings are first saved.
export function fromPreferences(get: <T>(key: string, fallback: T) => T): Typography {
  const saved = get<unknown>('reader.typography', null)
  if (saved !== null) return normalize(saved)
  return normalize({ size: get<unknown>('readerSize', DEFAULTS.size), font: get<unknown>('readerFont', DEFAULTS.font) })
}

// The line length is kept in characters, so changing the text size does not change how many characters fit on a line.
export const measurePx = (t: Typography): number => Math.round(t.width * t.size * FONTS[t.font].charWidth)

// What the page gets: CSS variables on the document.
export function toCssVars(t: Typography): Record<string, string> {
  return {
    '--r-size': `${t.size}px`,
    '--r-font': FONTS[t.font].stack,
    '--r-weight': String(t.weight),
    '--r-measure': `${measurePx(t)}px`,
    '--r-line': String(t.line),
    '--r-letter': `${t.letter}em`,
    '--r-word': `${t.word}em`,
    '--r-align': t.align,
    // Words are only hyphenated when the text is justified, where it prevents big gaps; elsewhere a word stays whole.
    '--r-hyphens': t.align === 'justify' ? 'auto' : 'manual',
  }
}

// One step of the − and + buttons.
export const stepSize = (size: number, direction: 1 | -1): number => clamp(size + direction * LIMITS.size.step, LIMITS.size)

export const widthLabel = (width: number): string => `about ${width} characters`
export const spacingLabel = (value: number, limit: Limit): string => (value <= limit.min ? 'Standard' : `+${Math.round(value * 100)}%`)

const LANGUAGE_CODES: Record<string, string> = { dutch: 'nl', polish: 'pl', french: 'fr', english: 'en', german: 'de', spanish: 'es', italian: 'it', portuguese: 'pt' }
// Lets the browser hyphenate in the right language; unknown languages get no code.
export const languageCode = (name: string): string | undefined => LANGUAGE_CODES[name.trim().toLowerCase()]

// Starting points on the Appearance page; each is a full set of settings, so choosing one changes everything at once.
export type Preset = { id: string; label: string; hint: string; values: Typography }
export const PRESETS: Preset[] = [
  { id: 'comfortable', label: 'Comfortable', hint: 'Easy on the eyes', values: DEFAULTS },
  { id: 'compact', label: 'Compact', hint: 'More text on screen', values: { ...DEFAULTS, size: 16, width: 95, line: 1.6 } },
  { id: 'large', label: 'Large print', hint: 'Big and airy', values: { ...DEFAULTS, size: 24, weight: 500, width: 55, line: 2.2, letter: 0.02, word: 0.05 } },
  { id: 'book', label: 'Book', hint: 'Serif, justified', values: { ...DEFAULTS, size: 20, font: 'serif', width: 60, line: 1.9, align: 'justify' } },
]

// The preset these settings are exactly equal to, or null once you have changed anything.
export function matchingPreset(t: Typography): string | null {
  const same = (a: Typography, b: Typography) => (Object.keys(a) as (keyof Typography)[]).every((k) => a[k] === b[k])
  return PRESETS.find((p) => same(normalize(p.values), t))?.id ?? null
}
