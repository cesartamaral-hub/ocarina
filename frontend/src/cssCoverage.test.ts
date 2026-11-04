/// <reference types="node" />
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
const css = readFileSync(new URL('./index.css', import.meta.url), 'utf-8') // read directly: the test runner leaves styles out of imports

// A style rule that goes missing leaves the feature working but invisible (the audio highlight, the hover card, the
// picked-words bar all did). This lists every plain class name used in a component and fails when the stylesheet has no rule for it.
const sources = import.meta.glob('./**/*.tsx', { query: '?raw', import: 'default', eager: true }) as Record<string, string>

// Class names that are only hooks for the code or the markup's meaning, with no style of their own.
const WITHOUT_STYLE = new Set(['def-entry', 'settings-links'])

export function classNamesIn(source: string): string[] {
  const found = new Set<string>()
  for (const m of source.matchAll(/className=(?:"([^"]*)"|\{`([^`]*)`\}|\{['"]([^'"]*)['"]\})/g)) {
    const text = (m[1] ?? m[2] ?? m[3] ?? '').replace(/\$\{[^}]*\}/g, ' ')
    for (const name of text.split(/\s+/)) {
      if (/^[A-Za-z][\w-]*$/.test(name) && !name.endsWith('-') && name !== 's') found.add(name) // "pal-" and "s" are the start of a built name
    }
  }
  return [...found]
}

describe('classNamesIn', () => {
  it('finds plain and template class names and leaves out built ones', () => {
    expect(classNamesIn('<a className="button small" /><b className={`w s${x}${y ? \' sel\' : \'\'}`} /><i className={cond ? \'a\' : \'b\'} />')).toEqual(['button', 'small', 'w'])
    expect(classNamesIn('<i className={`pal-${p}`} />')).toEqual([])
  })
})

describe('the stylesheet', () => {
  it('is read', () => {
    expect(css.length).toBeGreaterThan(10_000)
  })

  it('has a rule for every class the components use', () => {
    const missing = new Set<string>()
    for (const [file, source] of Object.entries(sources)) {
      for (const name of classNamesIn(source)) {
        if (!WITHOUT_STYLE.has(name) && !new RegExp(`\\.${name.replace(/[-]/g, '\\-')}(?![\\w-])`).test(css)) missing.add(`${name} (${file})`)
      }
    }
    expect([...missing]).toEqual([])
  })
})
