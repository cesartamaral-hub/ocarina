// Where to put a popover that opens from a button: just below it, lined up with its left or right edge, never outside the window.
export type Placement = { top: number; left: number; width: number; maxHeight: number }

export function placePopover(
  anchor: { left: number; right: number; bottom: number },
  width: number,
  align: 'start' | 'end',
  viewport: { width: number; height: number },
  margin = 8,
): Placement {
  const w = Math.min(width, viewport.width - 2 * margin)
  const wanted = align === 'end' ? anchor.right - w : anchor.left
  const left = Math.max(margin, Math.min(wanted, viewport.width - w - margin))
  const top = anchor.bottom + 6
  return { top, left, width: w, maxHeight: Math.max(160, viewport.height - top - margin) }
}
