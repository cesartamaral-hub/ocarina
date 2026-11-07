// Where to put a popover that opens from a button: just below it (above it when the button is at the bottom of the window and there is
// more room there), lined up with its left or right edge, never outside the window.
export type Placement = { top?: number; bottom?: number; left: number; width: number; maxHeight: number }

export function placePopover(
  anchor: { left: number; right: number; bottom: number; top?: number },
  width: number,
  align: 'start' | 'end',
  viewport: { width: number; height: number },
  margin = 8,
): Placement {
  const w = Math.min(width, viewport.width - 2 * margin)
  const wanted = align === 'end' ? anchor.right - w : anchor.left
  const left = Math.max(margin, Math.min(wanted, viewport.width - w - margin))
  const top = anchor.bottom + 6
  const room = viewport.height - top - margin
  if (anchor.top !== undefined && room < 200 && anchor.top > room) {
    return { bottom: viewport.height - anchor.top + 6, left, width: w, maxHeight: anchor.top - 6 - margin }
  }
  return { top, left, width: w, maxHeight: Math.max(160, viewport.height - top - margin) }
}
