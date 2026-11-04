import { useCallback, useEffect, useRef, useState } from 'react'
import { placePopover, type Placement } from './placement'

// Where a popover opened by a button goes, and the button's ref; the popover closes when the window is resized.
export function useAnchoredPopover(width: number, align: 'start' | 'end' = 'start') {
  const anchor = useRef<HTMLButtonElement>(null)
  const [placement, setPlacement] = useState<Placement | null>(null)
  const close = useCallback(() => setPlacement(null), [])
  const toggle = () => {
    const rect = anchor.current?.getBoundingClientRect()
    if (placement || !rect) return close()
    setPlacement(placePopover(rect, width, align, { width: window.innerWidth, height: window.innerHeight }))
  }
  useEffect(() => {
    if (!placement) return
    window.addEventListener('resize', close)
    return () => window.removeEventListener('resize', close)
  }, [placement, close])
  return { anchor, placement, toggle, close }
}

