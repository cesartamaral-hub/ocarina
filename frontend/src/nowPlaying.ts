import { useEffect, type RefObject } from 'react'
import type { Playable } from './media'
import { jumpTarget } from './audioJump'

// Tells the system what is playing, as a music player does: the title and artist in the Now Playing display, and the media keys,
// the headphone buttons and the lock-screen controls (play, pause, previous and next sentence, back and forward, seeking).
export function useNowPlaying(audioRef: RefObject<Playable | null>, info: { title: string; artist: string; starts: number[] | null } | null) {
  const title = info?.title
  const artist = info?.artist
  const starts = info?.starts ?? null
  useEffect(() => {
    if (!title || !('mediaSession' in navigator)) return
    const session = navigator.mediaSession
    session.metadata = new MediaMetadata({
      title,
      artist: artist ?? '',
      album: 'Ocarina',
      artwork: [{ src: `${import.meta.env.BASE_URL}ocarina-icon.png`, sizes: '1024x1024', type: 'image/png' }],
    })
    const audio = () => audioRef.current
    const jump = (direction: 'back' | 'forward') => {
      const el = audio()
      if (el) el.currentTime = jumpTarget(direction, el.currentTime, el.duration, starts)
    }
    const handlers: [MediaSessionAction, MediaSessionActionHandler][] = [
      ['play', () => void audio()?.play().catch(() => undefined)],
      ['pause', () => audio()?.pause()],
      ['previoustrack', () => jump('back')],
      ['nexttrack', () => jump('forward')],
      ['seekbackward', (d) => { const el = audio(); if (el) el.currentTime = Math.max(0, el.currentTime - (d.seekOffset ?? 10)) }],
      ['seekforward', (d) => { const el = audio(); if (el) el.currentTime = Math.min(el.duration || Infinity, el.currentTime + (d.seekOffset ?? 10)) }],
      ['seekto', (d) => { const el = audio(); if (el && d.seekTime !== undefined) el.currentTime = d.seekTime }],
    ]
    for (const [action, handler] of handlers) {
      try {
        session.setActionHandler(action, handler)
      } catch {
        /* this web view does not know the action */
      }
    }
    // The position in the system's display follows the player.
    const last = { at: 0 }
    const report = () => {
      const el = audio()
      if (!el || !Number.isFinite(el.duration) || Date.now() - last.at < 1000) return
      last.at = Date.now()
      try {
        session.setPositionState({ duration: el.duration, position: Math.min(el.currentTime, el.duration), playbackRate: el.playbackRate || 1 })
      } catch {
        /* a position outside the audio */
      }
    }
    const timer = window.setInterval(report, 1000) // an audio element or a video: neither needs to be there yet
    return () => {
      window.clearInterval(timer)
      session.metadata = null
      for (const [action] of handlers) {
        try {
          session.setActionHandler(action, null)
        } catch {
          /* ignore */
        }
      }
    }
  }, [audioRef, title, artist, starts])
}
