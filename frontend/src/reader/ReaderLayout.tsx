import { useCallback, useEffect, useRef, useState, type KeyboardEvent, type PointerEvent, type ReactNode } from 'react'
import { getPref, setPref } from '../api'
import { actionFor } from '../shortcutKeys'
import { SIDE_DEFAULT, SIDE_MAX, SIDE_MIN, clampWidth, widthAfterKey } from './sidePanel'

// The reader's frame: the reading column on the left and the word panel pinned to the right edge of the window.
// The panel can be resized (drag the handle, or focus it and use the arrow keys; double-click resets), collapsed to a
// narrow rail, and on a narrow window becomes a drawer that slides over the text while a word is selected.
export function ReaderLayout({
  main,
  side,
  selectionKey,
  onCloseDrawer,
}: {
  main: ReactNode
  side: ReactNode
  selectionKey: string | null // identifies what is selected; null when nothing is
  onCloseDrawer: () => void
}) {
  const hasSelection = selectionKey !== null
  const [width, setWidth] = useState(() => clampWidth(getPref('reader.sideWidth', SIDE_DEFAULT)))
  const [collapsed, setCollapsed] = useState(() => getPref('reader.sideCollapsed', false))
  const dragging = useRef(false)

  const toggle = useCallback(() => {
    setCollapsed((c) => {
      setPref('reader.sideCollapsed', !c)
      return !c
    })
  }, [])

  // Picking a word while the panel is collapsed opens it: that is what the panel is for.
  const lastKey = useRef<string | null>(null)
  useEffect(() => {
    if (selectionKey !== null && selectionKey !== lastKey.current && collapsed) toggle()
    lastKey.current = selectionKey
  }, [selectionKey, collapsed, toggle])

  // The key that shows or hides the panel.
  useEffect(() => {
    function onKey(e: globalThis.KeyboardEvent) {
      const tag = (e.target as HTMLElement).tagName
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(tag) || e.metaKey || e.ctrlKey || e.altKey) return
      if (actionFor(e)?.id === 'togglePanel') {
        e.preventDefault()
        toggle()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [toggle])

  const commit = (w: number) => {
    const next = clampWidth(w)
    setWidth(next)
    setPref('reader.sideWidth', next)
  }

  function onPointerDown(e: PointerEvent<HTMLDivElement>) {
    e.currentTarget.setPointerCapture(e.pointerId)
    dragging.current = true
  }
  function onPointerMove(e: PointerEvent<HTMLDivElement>) {
    if (dragging.current) setWidth(clampWidth(window.innerWidth - e.clientX)) // live; saved when you let go
  }
  function onPointerUp(e: PointerEvent<HTMLDivElement>) {
    if (!dragging.current) return
    dragging.current = false
    e.currentTarget.releasePointerCapture(e.pointerId)
    commit(window.innerWidth - e.clientX)
  }
  function onHandleKey(e: KeyboardEvent<HTMLDivElement>) {
    const next = widthAfterKey(e.key, width, e.shiftKey)
    if (next === null) return
    e.preventDefault()
    commit(next)
  }

  return (
    <div
      className={`reader${collapsed ? ' collapsed' : ''}${hasSelection ? ' drawer-open' : ''}`}
      style={{ '--side-w': `${width}px` } as React.CSSProperties}
    >
      <div className="reader-main">{main}</div>
      <div className="reader-scrim" onClick={onCloseDrawer} aria-hidden="true" />
      <aside className="reader-side" aria-label="Word panel">
        <div
          className="side-handle"
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize the word panel"
          aria-valuemin={SIDE_MIN}
          aria-valuemax={SIDE_MAX}
          aria-valuenow={width}
          tabIndex={0}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onKeyDown={onHandleKey}
          onDoubleClick={() => commit(SIDE_DEFAULT)}
        />
        <div className="side-bar">
          <button
            className="secondary side-toggle"
            onClick={toggle}
            aria-expanded={!collapsed}
            title={collapsed ? 'Show the word panel (P)' : 'Hide the word panel (P)'}
            aria-label={collapsed ? 'Show the word panel' : 'Hide the word panel'}
          >
            {collapsed ? '‹' : '›'}
          </button>
          <button className="secondary side-close" onClick={onCloseDrawer} aria-label="Close the word panel">
            ✕
          </button>
        </div>
        <div className="side-body">{side}</div>
      </aside>
    </div>
  )
}
