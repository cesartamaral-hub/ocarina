import { useEffect, useRef, useState, type ReactNode, type RefObject } from 'react'
import { useOffline } from './offline'
import { getPref, setPref } from './api'
import { keyLabel, keyOf } from './shortcutKeys'
import type { Playable } from './media'
import { SPEED, clampSpeed, speedLabel } from './speeds'
import { SpeedMenu } from './SpeedMenu'
import { ERRORS, YouTubeMedia, loadYouTube } from './youtube'

// The book's video, for a book made from a YouTube link: the video player and the speed control, in place of the audio bar.
// It fills audioRef with something that plays like an audio element, so the reader's keys, the media keys and the sentences
// that light up work on the video too.
export function VideoBar({
  videoId,
  language,
  audioRef,
  onTime,
  children,
}: {
  videoId: string
  language: string
  audioRef: RefObject<Playable | null>
  onTime?: (seconds: number) => void
  children?: ReactNode
}) {
  const offline = useOffline()
  const host = useRef<HTMLDivElement>(null)
  const [speed, setSpeed] = useState(() => clampSpeed(getPref<number>(`speed.${language}`, 1)))
  const speedNow = useRef(speed)
  const onTimeNow = useRef(onTime)
  const [problem, setProblem] = useState('')
  const [large, setLarge] = useState(() => getPref<boolean>('video.large', true)) // big and centred above the text, or small beside the controls

  useEffect(() => {
    speedNow.current = speed
    onTimeNow.current = onTime
  })

  const choose = (value: number) => {
    const s = clampSpeed(value)
    setSpeed(s)
    setPref(`speed.${language}`, s)
    if (audioRef.current) audioRef.current.playbackRate = s
  }

  useEffect(() => {
    const run = { alive: true, stop: () => {} }
    if (offline) return // the player comes from YouTube
    loadYouTube().then(
      (YT) => {
        if (!run.alive || !host.current) return
        const holder = document.createElement('div')
        host.current.replaceChildren(holder)
        const timer = window.setInterval(() => {
          const el = audioRef.current
          if (el && !el.paused) onTimeNow.current?.(el.currentTime)
        }, 200)
        const player = new YT.Player(holder, {
          videoId,
          width: '100%',
          height: '100%',
          playerVars: { playsinline: 1, rel: 0, origin: window.location.origin },
          events: {
            onReady: () => {
              const media = new YouTubeMedia(player)
              audioRef.current = media
              media.playbackRate = speedNow.current
            },
            onStateChange: () => {
              if (audioRef.current) onTimeNow.current?.(audioRef.current.currentTime)
            },
            onError: (e: { data: number }) => setProblem(ERRORS[e.data] ?? 'The video cannot be played here.'),
          },
        })
        run.stop = () => {
          window.clearInterval(timer)
          player.destroy()
        }
      },
      (e: Error) => setProblem(e.message),
    )
    return () => {
      run.alive = false
      run.stop()
      audioRef.current = null
    }
  }, [videoId, audioRef, offline])

  return (
    <>
      <div className={`video-stage${large ? ' large' : ''}`}>
      <div className="video-frame">
        {offline ? (
          <p className="video-problem">The video needs the internet (Work offline is on).</p>
        ) : problem ? (
          <p className="video-problem">
            {problem} <a href={`https://www.youtube.com/watch?v=${videoId}`} target="_blank" rel="noreferrer">Open it on YouTube</a>
          </p>
        ) : (
          <div ref={host} className="video-host" />
        )}
      </div>
      </div>
      <div className="controls">
        <div className="speed-control">
          <label>
            Speed {speedLabel(speed)}
            <input type="range" min={SPEED.min} max={SPEED.max} step={SPEED.step} value={speed} aria-valuetext={speedLabel(speed)} onChange={(e) => choose(Number(e.target.value))} />
          </label>
          <SpeedMenu speed={speed} onChange={choose} />
        </div>
        <button
          className="secondary"
          aria-pressed={large}
          onClick={() => {
            setLarge(!large)
            setPref('video.large', !large)
          }}
        >
          {large ? 'Smaller video' : 'Larger video'}
        </button>
        {children}
      </div>
      <p className="muted key-hint">
        <kbd>{keyLabel(keyOf('skipBack'))}</kbd> back · <kbd>{keyLabel(keyOf('playPause'))}</kbd> play or pause · <kbd>{keyLabel(keyOf('skipForward'))}</kbd> forward · the video's speeds are 0.25 to 2
      </p>
    </>
  )
}
