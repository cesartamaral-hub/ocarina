// Small rules for the text editor.

// Words as the reader would count them: runs of letters or digits, in any script. Good enough for a live count.
export function wordCount(text: string): number {
  return text.match(/[\p{L}\p{N}][\p{L}\p{N}'’-]*/gu)?.length ?? 0
}

// Paragraphs are separated by blank lines.
export function paragraphCount(text: string): number {
  return text.split(/\n\s*\n/).filter((p) => p.trim()).length
}

// Line endings and trailing space do not count as a change.
const plain = (text: string) => text.replace(/\r\n/g, '\n').trimEnd()
export const isDirty = (current: string, original: string): boolean => plain(current) !== plain(original)

// The whole material is edited as one text. A page ends where a line says this; a line can be moved, added or deleted like any other.
export const PAGE_BREAK = '~~~ page break ~~~'
const BREAK_LINE = /^[ \t]*~~~ page break ~~~[ \t]*$/m

export const joinPages = (pages: string[]): string =>
  pages.map((p) => p.replace(/\s+$/, '')).join(`\n\n${PAGE_BREAK}\n\n`)

// Pages as they will be saved: split at the break lines, empty pages dropped.
export const splitPages = (text: string): string[] =>
  text
    .replace(/\r\n/g, '\n')
    .split(new RegExp(BREAK_LINE.source, 'gm'))
    .map((p) => p.trim())
    .filter((p) => p !== '')

// Which page (1-based) a position in the text falls on: one more than the break lines before it.
export const pageAt = (text: string, offset: number): number =>
  (text.slice(0, offset).match(new RegExp(BREAK_LINE.source, 'gm'))?.length ?? 0) + 1

const escapeRe = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
const finder = (find: string, matchCase: boolean) => new RegExp(escapeRe(find), matchCase ? 'g' : 'gi')

export const countMatches = (text: string, find: string, matchCase: boolean): number =>
  find ? (text.match(finder(find, matchCase))?.length ?? 0) : 0

export const replaceAll = (text: string, find: string, replacement: string, matchCase: boolean): string =>
  find ? text.replace(finder(find, matchCase), () => replacement) : text

// Where the next match starts at or after `from`, wrapping round to the top; -1 for none.
export function nextMatch(text: string, find: string, from: number, matchCase: boolean): number {
  if (!find) return -1
  const re = finder(find, matchCase)
  re.lastIndex = from
  const hit = re.exec(text) ?? ((re.lastIndex = 0), re.exec(text))
  return hit ? hit.index : -1
}
