import { describe, expect, it } from 'vitest'
import { parseNotes } from './changelog'

describe('parseNotes', () => {
  it('splits markdown into headings, items and paragraphs', () => {
    expect(parseNotes('## What is new\n\n- Faster **sync**\n* Fixes `a bug`\n1. Third\nSome words.')).toEqual([
      { type: 'heading', text: 'What is new' },
      { type: 'item', text: 'Faster sync' },
      { type: 'item', text: 'Fixes a bug' },
      { type: 'item', text: 'Third' },
      { type: 'text', text: 'Some words.' },
    ])
  })
  it('keeps the words of links and drops images and rules', () => {
    expect(parseNotes('See [the docs](https://x.y/z) now\n---\n![shot](a.png)')).toEqual([{ type: 'text', text: 'See the docs now' }])
  })
  it('is empty for empty notes', () => {
    expect(parseNotes('  \n')).toEqual([])
  })
})
