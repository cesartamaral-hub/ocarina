import { useCallback, useEffect, useRef, useState } from 'react'
import { getJob, getSentences, startAudio, type BookSentences, type Job } from './api'

const SPEED_KEY = 'ocarina.speed'
const MIN_SPEED = 0.5

function loadSpeed(language: string): number {
  try {
    const saved = JSON.parse(localStorage.getItem(SPEED_KEY) ?? '{}')
    return saved[language] ?? 1
  } catch {
    return 1
  }
}

function saveSpeed(language: string, speed: number) {
  try {
    const saved = JSON.parse(localStorage.getItem(SPEED_KEY) ?? '{}')
    localStorage.setItem(SPEED_KEY, JSON.stringify({ ...saved, [language]: speed }))
  } catch {
    // Storage can be unavailable; the speed just won't be remembered.
  }
}

export function BookView({ bookId }: { bookId: number }) {
  const [book, setBook] = useState<BookSentences | null>(null)
  const [error, setError] = useState('')
  const [job, setJob] = useState<Job | null>(null)
  const [audioVersion, setAudioVersion] = useState(0)
  const [speed, setSpeed] = useState(1)
  const [pause, setPause] = useState(0.5)
  const [current, setCurrent] = useState(-1)
  const audio = useRef<HTMLAudioElement>(null)

  const load = useCallback(() => {
    getSentences(bookId).then(
      (b) => {
        setBook(b)
        setSpeed(loadSpeed(b.language))
      },
      (e) => setError(e.message),
    )
  }, [bookId])
  useEffect(load, [load])

  // Pitch-preserving slow playback; applied again whenever the audio element is replaced.
  useEffect(() => {
    const el = audio.current
    if (!el) return
    el.playbackRate = speed
    el.preservesPitch = true
  }, [speed, audioVersion, book?.hasAudio])

  // Poll a running job until it finishes.
  useEffect(() => {
    if (!job || job.state !== 'running') return
    const timer = setInterval(async () => {
      const j = await getJob(job.id)
      setJob(j)
      if (j.state === 'done') {
        setAudioVersion((v) => v + 1)
        load()
      }
    }, 700)
    return () => clearInterval(timer)
  }, [job, load])

  async function generate(replace = false) {
    try {
      setJob(await startAudio(bookId, { replace, pause }))
    } catch (e) {
      const err = e as Error & { code?: string }
      if (err.code === 'has_user_audio') {
        if (window.confirm('This book has your own audio. Replace it with generated audio?')) {
          generate(true)
        }
      } else {
        setError(err.message)
      }
    }
  }

  function onTimeUpdate() {
    if (!book?.hasTimings || !audio.current) return
    const t = audio.current.currentTime
    let idx = -1
    book.sentences.forEach((s, i) => {
      if (s.start !== undefined && s.start <= t) idx = i
    })
    setCurrent(idx)
  }

  function playFrom(start?: number) {
    const el = audio.current
    if (!el || start === undefined) return
    el.currentTime = start
    el.play()
  }

  if (error) return <p className="error">{error}</p>
  if (!book) return <p className="muted">Loading…</p>

  const running = job?.state === 'running'
  return (
    <>
      <p>
        <a href="#/">← Books</a>
      </p>
      <h1>{book.title}</h1>
      <p className="muted">
        {book.language} · <a href={`/read/${book.id}`}>Open in Lute reader</a>
      </p>

      <section className="panel">
        {book.hasAudio && (
          <audio
            ref={audio}
            key={audioVersion}
            controls
            src={`/useraudio/stream/${book.id}?v=${audioVersion}`}
            onTimeUpdate={onTimeUpdate}
            onLoadedMetadata={() => {
              if (audio.current) {
                audio.current.playbackRate = speed
                audio.current.preservesPitch = true
              }
            }}
          />
        )}
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
                saveSpeed(book.language, s)
              }}
            />
          </label>
          <label>
            Pause between sentences {pause.toFixed(1)} s
            <input
              type="range"
              min={0.2}
              max={2}
              step={0.1}
              value={pause}
              onChange={(e) => setPause(Number(e.target.value))}
            />
          </label>
          <button disabled={running} onClick={() => generate()}>
            {book.hasAudio ? 'Regenerate audio' : 'Generate audio'}
          </button>
        </div>
        {job && running && (
          <div className="progress">
            <progress value={job.done} max={job.total || 1} />
            <span className="muted">
              {job.done} / {job.total || '…'} sentences
            </span>
          </div>
        )}
        {job?.state === 'error' && <p className="error">{job.error}</p>}
        {book.hasAudio && !book.hasTimings && (
          <p className="muted">This audio was not generated by Ocarina, so sentences can't follow it.</p>
        )}
      </section>

      <ol className="sentences">
        {book.sentences.map((s, i) => (
          <li
            key={i}
            className={i === current ? 'current' : ''}
            onClick={() => playFrom(s.start)}
            ref={(el) => {
              if (el && i === current) el.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
            }}
          >
            {s.text}
          </li>
        ))}
      </ol>
    </>
  )
}
