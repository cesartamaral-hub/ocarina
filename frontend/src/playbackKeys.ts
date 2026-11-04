import { useEffect, type RefObject } from 'react'
import { jumpTarget } from './audioJump'
import { actionFor } from './shortcutKeys'

// Keyboard control of the audio player: play or pause, and jump back or forward (see audioJump.ts).
// starts: sentence start times when the audio has timings, else null. Does nothing when there is no player on
// the page, or while you type in a field.
export function usePlaybackKeys(audioRef: RefObject<HTMLAudioElement | null>, starts: number[] | null) {
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const target = e.target as HTMLElement
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName) || target.isContentEditable) return
      if (e.metaKey || e.ctrlKey || e.altKey) return
      const id = actionFor(e)?.id
      const audio = audioRef.current
      if (!audio || (id !== 'playPause' && id !== 'skipBack' && id !== 'skipForward')) return
      e.preventDefault()
      if (id === 'playPause') {
        if (e.repeat) return // holding the key should not flicker between play and pause
        if (audio.paused) audio.play().catch(() => undefined)
        else audio.pause()
      } else {
        audio.currentTime = jumpTarget(id === 'skipBack' ? 'back' : 'forward', audio.currentTime, audio.duration, starts)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [audioRef, starts])
}
