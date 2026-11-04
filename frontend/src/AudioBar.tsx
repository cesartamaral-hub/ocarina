import { useEffect, useState, type ReactNode, type RefObject } from 'react'
import { getPref, setPref } from './api'
import { keyLabel, keyOf } from './shortcutKeys'

const MIN_SPEED = 0.5

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
  audioRef: RefObject<HTMLAudioElement | null>
  onTime?: (seconds: number) => void
  children?: ReactNode
}) {
  const [speed, setSpeed] = useState(() => getPref<number>(`speed.${language}`, 1))

  // Applied again whenever the audio element is replaced (new version).
  useEffect(() => {
    const el = audioRef.current
    if (!el) return
    el.playbackRate = speed
    el.preservesPitch = true
  }, [speed, version, audioRef])

  return (
    <>
      <audio
        ref={audioRef}
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
        <label>
          Speed {speed.toFixed(2)}×
          <input
            type="range"
            min={MIN_SPEED}
            max={1}
            step={0.05}
            value={speed}
            onChange={(e) => {
              const s = Number(e.target.value)
              setSpeed(s)
              setPref(`speed.${language}`, s)
            }}
          />
        </label>
        {children}
      </div>
      <p className="muted key-hint">
        <kbd>{keyLabel(keyOf('skipBack'))}</kbd> back · <kbd>{keyLabel(keyOf('playPause'))}</kbd> play or pause · <kbd>{keyLabel(keyOf('skipForward'))}</kbd> forward
      </p>
    </>
  )
}
