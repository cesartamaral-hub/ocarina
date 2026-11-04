// Playback speeds: the slider's range and the presets in the menu next to it.
export const SPEED = { min: 0.5, max: 2, step: 0.05 }
export const SPEED_PRESETS = [0.5, 0.75, 0.85, 1, 1.5, 2]

// A saved or typed speed made valid: inside the range, on the slider's steps.
export function clampSpeed(value: unknown): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) return 1
  const stepped = Math.round(value / SPEED.step) * SPEED.step
  return Math.round(Math.min(Math.max(stepped, SPEED.min), SPEED.max) * 100) / 100
}

export const speedLabel = (speed: number): string => `${speed.toFixed(2)}×`

// The preset equal to this speed, if there is one (to mark it in the menu).
export const presetFor = (speed: number): number | undefined => SPEED_PRESETS.find((p) => Math.abs(p - speed) < 0.001)
