import { useEffect, useRef } from 'react'

// What Esc does: it closes the innermost open thing (a menu, a popover, a selection), and when nothing is open
// it goes back one level. Things that can be closed register themselves here while they are open.

type Layer = { close: () => void }
const layers: Layer[] = []

export function useEscape(active: boolean, close: () => void): void {
  const latest = useRef(close)
  useEffect(() => {
    latest.current = close
  })
  useEffect(() => {
    if (!active) return
    const layer: Layer = { close: () => latest.current() }
    layers.push(layer)
    return () => {
      const at = layers.indexOf(layer)
      if (at >= 0) layers.splice(at, 1)
    }
  }, [active])
}

// Closes the innermost layer; false when there was none.
export function closeTopLayer(): boolean {
  const top = layers[layers.length - 1]
  if (!top) return false
  top.close()
  return true
}

// The page one level up from a route, or null on the book list.
export function parentRoute(hash: string): string | null {
  const audio = hash.match(/^#\/book\/(\d+)\/audio/)
  if (audio) return `#/book/${audio[1]}` // opens the book where you left off
  if (/^#\/book\/\d+/.test(hash)) return '#/'
  if (/^#\/settings\/languages\/(new|add|\d+)$/.test(hash)) return '#/settings/languages'
  if (hash === '' || hash === '#' || hash === '#/') return null
  return '#/'
}

// The parts of a keydown event this needs (so it can be tested without a browser).
export type KeyLike = {
  key: string
  metaKey: boolean
  ctrlKey: boolean
  altKey: boolean
  isComposing?: boolean
  target: unknown
  preventDefault: () => void
  stopImmediatePropagation: () => void
}

// Esc keydown handler for the whole window (installed once, in the capture phase). It always cancels the key's
// default so the window does not leave full screen.
export function onEscapeKey(e: KeyLike, go: (hash: string) => void, hash: () => string): void {
  if (e.key !== 'Escape' || e.metaKey || e.ctrlKey || e.altKey || e.isComposing) return
  e.preventDefault()
  e.stopImmediatePropagation()
  if (closeTopLayer()) return
  const target = e.target as { tagName?: string; blur?: () => void } | null
  if (target?.tagName && ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)) {
    target.blur?.() // first Esc leaves the field, the next one goes back
    return
  }
  const parent = parentRoute(hash())
  if (parent !== null) go(parent)
}
