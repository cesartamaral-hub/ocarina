// The word panel's width rules (kept apart from the component so they can be tested).
export const SIDE_DEFAULT = 380
export const SIDE_MIN = 320
export const SIDE_MAX = 560
export const STEP = 16

// Anything that is not a number (a damaged saved preference) becomes the default width.
export const clampWidth = (w: unknown): number =>
  typeof w === 'number' && Number.isFinite(w) ? Math.min(Math.max(Math.round(w), SIDE_MIN), SIDE_MAX) : SIDE_DEFAULT

// The width after a key press on the resize handle, or null for a key that does nothing. The handle is the
// panel's left edge, so left makes the panel wider. Shift takes bigger steps.
export function widthAfterKey(key: string, width: number, shift: boolean): number | null {
  const step = shift ? STEP * 3 : STEP
  switch (key) {
    case 'ArrowLeft':
      return clampWidth(width + step)
    case 'ArrowRight':
      return clampWidth(width - step)
    case 'Home':
      return SIDE_MIN
    case 'End':
      return SIDE_MAX
    case 'Enter':
      return SIDE_DEFAULT
    default:
      return null
  }
}
