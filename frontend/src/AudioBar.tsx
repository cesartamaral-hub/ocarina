import { useEffect, useState, type ReactNode, type RefObject } from 'react'
import { getPref, setPref } from './api'
import { keyLabel, keyOf } from './shortcutKeys'
import { SPEED, clampSpeed, speedLabel } from './speeds'
import { SpeedMenu } from './SpeedMenu'
import type { Playable } from './media'


// The book's audio player with a slow-down control (pitch preserved, remembered per language).
// children go in the controls row, after the speed slider.
export function AudioBar({
  bookId,
  language,
  version,
  audioRef,
  onTime,
  children,
}: {
  bookId: number
  language: string
  version: number
  audioRef: RefObject<Playable | null>
  onTime?: (seconds: number) => void
  children?: ReactNode
}) {
  const [speed, setSpeed] = useState(() => clampSpeed(getPref<number>(`speed.${language}`, 1)))

  const choose = (value: number) => {
    const s = clampSpeed(value)
    setSpeed(s)
    setPref(`speed.${language}`, s)
  }

  // Applied again whenever the audio element is replaced (new version).
  useEffect(() => {
    const el = audioRef.current as HTMLAudioElement | null
    if (!el) return
    el.playbackRate = speed
    el.preservesPitch = true
  }, [speed, version, audioRef])

  return (
    <>
      <audio
        ref={audioRef as RefObject<HTMLAudioElement | null>}
        key={version}
        controls
        src={`/useraudio/stream/${bookId}?v=${version}`}
        onTimeUpdate={(e) => onTime?.(e.currentTarget.currentTime)}
        onLoadedMetadata={(e) => {
          e.currentTarget.playbackRate = speed
          e.currentTarget.preservesPitch = true
        }}
      />
      <div className="controls">
        <div className="speed-control">
          <label>
            Speed {speedLabel(speed)}
            <input type="range" min={SPEED.min} max={SPEED.max} step={SPEED.step} value={speed} aria-valuetext={speedLabel(speed)} onChange={(e) => choose(Number(e.target.value))} />
          </label>
          <SpeedMenu speed={speed} onChange={choose} />
        </div>
        {children}
      </div>
      <p className="muted key-hint">
        <kbd>{keyLabel(keyOf('skipBack'))}</kbd> back · <kbd>{keyLabel(keyOf('playPause'))}</kbd> play or pause · <kbd>{keyLabel(keyOf('skipForward'))}</kbd> forward
      </p>
    </>
  )
}
