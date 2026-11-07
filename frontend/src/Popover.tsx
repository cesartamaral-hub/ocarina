import { useEffect, useRef, type ReactNode, type RefObject } from 'react'
import { createPortal } from 'react-dom'
import { useEscape } from './escape'
import type { Placement } from './placement'

// A popover opened by a button (see useAnchoredPopover). It is drawn on the page itself, not inside the area the button is in, so no
// scrolling area can clip it and no panel can be painted over it.
export function Popover({
  anchor,
  placement,
  onClose,
  label,
  role = 'dialog',
  className = '',
  children,
}: {
  anchor: RefObject<HTMLElement | null>
  placement: Placement
  onClose: () => void
  label: string
  role?: 'dialog' | 'menu'
  className?: string
  children: ReactNode
}) {
  const box = useRef<HTMLDivElement>(null)
  useEscape(true, onClose)
  useEffect(() => {
    const away = (e: MouseEvent) => {
      const target = e.target as Node
      // A click in another popover (a menu opened from this one) is not a click away.
      if (!box.current?.contains(target) && !anchor.current?.contains(target) && !(target as Element).closest?.('.popover')) onClose()
    }
    document.addEventListener('mousedown', away)
    return () => document.removeEventListener('mousedown', away)
  }, [anchor, onClose])
  return createPortal(
    <div
      ref={box}
      className={`popover ${className}`}
      role={role}
      aria-label={label}
      style={{ top: placement.top, bottom: placement.bottom, left: placement.left, width: placement.width, maxHeight: placement.maxHeight }}
    >
      {children}
    </div>,
    document.body,
  )
}
