import { AudioBar } from '../AudioBar'
import { AudioVersions } from '../AudioVersions'
import { Popover } from '../Popover'
import { VideoBar } from '../VideoBar'
import { useAnchoredPopover } from '../useAnchoredPopover'
import type { useAudioFollow } from './useAudioFollow'

// The player below the text: one slim row (play bar, speed, the page's sentences), with the rarely used things (follow across pages,
// which audio version) behind "⋯". A recording's name is not shown unless there is more than one to pick from.
export function AudioPanel({
  bookId,
  language,
  audioVersion,
  onVersionChanged,
  audio,
  videoId,
  follow,
  onFollowChange,
}: {
  bookId: number
  language: string
  audioVersion: number
  onVersionChanged: () => void
  audio: ReturnType<typeof useAudioFollow>
  videoId?: string // the book has no audio, but a video to play
  follow: boolean
  onFollowChange: (follow: boolean) => void
}) {
  const { anchor, placement, toggle, close } = useAnchoredPopover(260, 'end')
  const controls = (
    <>
      {audio.firstStart !== undefined && (
        <button className="quiet small" onClick={() => audio.playAt(audio.firstStart!)} title="Play this page from its first sentence">
          ▶ This page
        </button>
      )}
      <button ref={anchor} className="quiet small icon" aria-label="More audio options" aria-haspopup="dialog" aria-expanded={placement !== null} title="More audio options" onClick={() => toggle()}>
        ⋯
      </button>
      {placement && (
        <Popover anchor={anchor} placement={placement} onClose={close} label="Audio options" className="audio-options-popover">
          {audio.timings && (
            <label className="inline">
              <input type="checkbox" checked={follow} onChange={(e) => onFollowChange(e.target.checked)} /> Follow across pages
            </label>
          )}
          {!videoId && <AudioVersions bookId={bookId} refreshKey={0} compact onChanged={onVersionChanged} />}
          <a href={`#/book/${bookId}/audio`}>All audio options</a>
        </Popover>
      )}
    </>
  )
  return (
    <section className="reader-audio" aria-label="Audio">
      {videoId ? (
        <VideoBar videoId={videoId} language={language} audioRef={audio.audioRef} onTime={audio.onAudioTime}>
          {controls}
        </VideoBar>
      ) : (
        <AudioBar compact bookId={bookId} language={language} version={audioVersion} audioRef={audio.audioRef} onTime={audio.onAudioTime}>
          {controls}
        </AudioBar>
      )}
      {audio.timings && !audio.aligned && (
        <p className="muted note">The page text no longer matches the generated audio, so sentences won't follow it.</p>
      )}
      {!audio.timings && !videoId && (
        <p className="muted note">
          Sentences can't follow this recording yet. <a href={`#/book/${bookId}/audio`}>Sync it with the text</a> to make them light up.
        </p>
      )}
    </section>
  )
}
