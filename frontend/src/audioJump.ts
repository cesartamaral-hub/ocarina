// Where J and L take the playback position. Browsers cannot play audio backwards, so "back" means "jump back".
//
// With sentence timings (audio Ocarina generated) the jumps follow sentences, which is what a learner wants:
// J replays the sentence you are in, or the one before it when you have only just started this one; L goes to
// the next sentence. Without timings (your own recordings) they jump a fixed number of seconds.

export const JUMP_SECONDS = 10
// Closer than this to the start of a sentence, "back" goes to the previous sentence instead of restarting it.
export const RESTART_WINDOW = 1

export type Direction = 'back' | 'forward'

// starts: sentence start times in ascending order, or null when the audio has no timings.
export function jumpTarget(direction: Direction, current: number, duration: number, starts: number[] | null): number {
  const end = Number.isFinite(duration) && duration > 0 ? duration : Infinity
  const clamp = (t: number) => Math.min(Math.max(t, 0), end)
  if (!starts || starts.length === 0) {
    return clamp(current + (direction === 'back' ? -JUMP_SECONDS : JUMP_SECONDS))
  }
  // The sentence being played: the last one that has started.
  let at = -1
  for (let i = 0; i < starts.length; i++) {
    if (starts[i] <= current) at = i
    else break
  }
  if (direction === 'forward') return at + 1 < starts.length ? clamp(starts[at + 1]) : clamp(end)
  if (at < 0) return 0
  return current - starts[at] > RESTART_WINDOW ? starts[at] : (starts[at - 1] ?? 0)
}
