import { describe, expect, it, vi } from 'vitest'
import { closeTopLayer, onEscapeKey, parentRoute, type KeyLike } from './escape'

describe('parentRoute', () => {
  it('goes from the reader to the book list, and from the audio page back to the book', () => {
    expect(parentRoute('#/book/12/read/3')).toBe('#/')
    expect(parentRoute('#/book/12/audio')).toBe('#/book/12') // which opens the reader where you were
    expect(parentRoute('#/book/12')).toBe('#/')
  })
  it('goes from settings pages to settings, and from settings to the list', () => {
    expect(parentRoute('#/appearance')).toBe('#/settings')
    expect(parentRoute('#/translation')).toBe('#/settings')
    expect(parentRoute('#/storage')).toBe('#/settings')
    expect(parentRoute('#/settings')).toBe('#/')
  })
  it('goes from a language to the languages list', () => {
    expect(parentRoute('#/languages/4')).toBe('#/languages')
    expect(parentRoute('#/languages/new')).toBe('#/languages')
    expect(parentRoute('#/languages')).toBe('#/')
  })
  it('stays on the book list', () => {
    expect(parentRoute('#/')).toBeNull()
    expect(parentRoute('')).toBeNull()
  })
})

describe('onEscapeKey', () => {
  const key = (over: Partial<KeyLike> = {}) => {
    const e = { key: 'Escape', metaKey: false, ctrlKey: false, altKey: false, target: null, prevented: false, preventDefault: () => (e.prevented = true), stopImmediatePropagation: () => undefined, ...over }
    return e as KeyLike & { prevented: boolean }
  }

  it('always cancels the key so the window stays in full screen', () => {
    const e = key()
    onEscapeKey(e, vi.fn(), () => '#/')
    expect(e.prevented).toBe(true)
  })
  it('goes back when nothing is open', () => {
    const go = vi.fn()
    onEscapeKey(key(), go, () => '#/book/5/audio')
    expect(go).toHaveBeenCalledWith('#/book/5')
  })
  it('leaves a text field first, and does not go back yet', () => {
    const go = vi.fn()
    const blur = vi.fn()
    onEscapeKey(key({ target: { tagName: 'TEXTAREA', blur } }), go, () => '#/book/5/read/2')
    expect(blur).toHaveBeenCalled()
    expect(go).not.toHaveBeenCalled()
  })
  it('ignores other keys and shortcuts', () => {
    const go = vi.fn()
    const other = key({ key: 'a' })
    onEscapeKey(other, go, () => '#/book/5')
    onEscapeKey(key({ metaKey: true }), go, () => '#/book/5')
    expect(go).not.toHaveBeenCalled()
    expect(other.prevented).toBe(false)
  })
  it('has no layer to close when none is open', () => {
    expect(closeTopLayer()).toBe(false)
  })
})
