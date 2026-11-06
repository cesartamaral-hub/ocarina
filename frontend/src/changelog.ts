// The release notes GitHub keeps as markdown, as a few plain blocks the update window can show: headings, bullet items and paragraphs.
export type NoteBlock = { type: 'heading' | 'item' | 'text'; text: string }

const plain = (s: string) =>
  s
    .replace(/!\[[^\]]*\]\([^)]*\)/g, '') // images
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1') // links keep their words
    .replace(/(\*\*|__|`)/g, '')
    .replace(/(^|\s)[*_]([^*_]+)[*_](?=\s|$)/g, '$1$2')
    .trim()

export function parseNotes(notes: string): NoteBlock[] {
  const blocks: NoteBlock[] = []
  for (const raw of notes.replace(/\r\n?/g, '\n').split('\n')) {
    const line = raw.trim()
    if (!line || /^[-*_]{3,}$/.test(line)) continue
    const heading = /^#{1,6}\s+(.*)$/.exec(line)
    const item = /^(?:[-*+]|\d+[.)])\s+(.*)$/.exec(line)
    const text = plain(heading?.[1] ?? item?.[1] ?? line)
    if (text) blocks.push({ type: heading ? 'heading' : item ? 'item' : 'text', text })
  }
  return blocks
}
