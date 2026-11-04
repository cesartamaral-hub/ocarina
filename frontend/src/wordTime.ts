// Where in a sentence's audio a word is said, found in proportion to the letters before it. The sentence runs until the next one
// starts, but that includes the pause after it, so a sentence is taken to last at most 0.1 s a letter.
export function wordTime(start: number, nextStart: number | undefined, charsBefore: number, chars: number): number {
  if (chars <= 0) return start
  const span = Math.min(nextStart !== undefined ? nextStart - start : Infinity, chars * 0.1)
  return start + (charsBefore / chars) * span
}
