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
