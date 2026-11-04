import { AudioBar } from '../AudioBar'
import { AudioVersions } from '../AudioVersions'
import { VideoBar } from '../VideoBar'
import type { useAudioFollow } from './useAudioFollow'

// The player above the text. It spans the reading column, stays in view while you read, and its controls wrap
// onto more rows only when the column is narrow.
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
  return (
    <section className="reader-audio" aria-label="Audio">
      {videoId ? (
        <VideoBar videoId={videoId} language={language} audioRef={audio.audioRef} onTime={audio.onAudioTime}>
          {audio.firstStart !== undefined && (
            <button className="secondary" onClick={() => audio.playAt(audio.firstStart!)}>
              ▶ Play this page
            </button>
          )}
          {audio.timings && (
            <label className="inline">
              <input type="checkbox" checked={follow} onChange={(e) => onFollowChange(e.target.checked)} /> Follow across pages
            </label>
          )}
        </VideoBar>
      ) : (
        <>
          <AudioVersions bookId={bookId} refreshKey={0} compact onChanged={onVersionChanged} />
          <AudioBar bookId={bookId} language={language} version={audioVersion} audioRef={audio.audioRef} onTime={audio.onAudioTime}>
        {audio.firstStart !== undefined && (
          <button className="secondary" onClick={() => audio.playAt(audio.firstStart!)}>
            ▶ Play this page
          </button>
        )}
        {audio.timings && (
          <label className="inline">
            <input type="checkbox" checked={follow} onChange={(e) => onFollowChange(e.target.checked)} /> Follow across pages
          </label>
        )}
          </AudioBar>
        </>
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
