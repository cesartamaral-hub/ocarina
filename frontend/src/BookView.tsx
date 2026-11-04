import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { AudioBar } from './AudioBar'
import {
  cancelJob,
  getActiveJobs,
  getAudioOptions,
  getJob,
  getSentences,
  isActive,
  startAudio,
  uploadAudio,
  type AudioOptions,
  type BookSentences,
  type AudioVersion,
  type Job,
  syncAudioVersion,
} from './api'
import { AudioOptionsMenu, type AudioChoice } from './AudioOptionsMenu'
import { AudioVersions } from './AudioVersions'
import { usePlaybackKeys } from './playbackKeys'

const modelName = (o: AudioOptions, id: string) => o.models.find((m) => m.id === id)?.name ?? id
const voiceName = (o: AudioOptions, id: string) => o.voices.find((v) => v.id === id)?.name ?? id

export function BookView({ bookId }: { bookId: number }) {
  const [book, setBook] = useState<BookSentences | null>(null)
  const [error, setError] = useState('')
  const [job, setJob] = useState<Job | null>(null)
  const [needsAligner, setNeedsAligner] = useState(false)
  const [audioVersion, setAudioVersion] = useState(0) // bumped when the player must load another file
  const [versionsKey, setVersionsKey] = useState(0) // bumped when a version was added or removed
  const [pause, setPause] = useState(0.5)
  const [current, setCurrent] = useState(-1)
  const [needsModel, setNeedsModel] = useState(false)
  const [options, setOptions] = useState<AudioOptions | null>(null)
  const [optionsError, setOptionsError] = useState('')
  const [choice, setChoice] = useState<AudioChoice>({ model: '', voice: '' })
  const audio = useRef<HTMLAudioElement>(null)
  const starts = useMemo(
    () => (book?.hasTimings ? book.sentences.map((s) => s.start).filter((t): t is number => t !== undefined) : null),
    [book],
  )
  usePlaybackKeys(audio, starts)

  const load = useCallback(() => {
    getSentences(bookId).then(
      (b) => setBook(b),
      (e) => setError(e.message),
    )
  }, [bookId])
  useEffect(load, [load])
  useEffect(() => {
    getAudioOptions(bookId).then(setOptions, (e) => setOptionsError(e.message))
  }, [bookId])

  // Coming back to a book whose audio is still being made (or waiting its turn) shows that job.
  useEffect(() => {
    getActiveJobs().then(
      (jobs) => setJob((cur) => cur ?? jobs.find((j) => (j.kind === 'audio' || j.kind === 'sync') && j.book_id === bookId) ?? null),
      () => undefined,
    )
  }, [bookId])

  // Poll a waiting or running job until it ends.
  const jobId = isActive(job) ? job!.id : null
  useEffect(() => {
    if (!jobId) return
    const timer = setInterval(async () => {
      const j = await getJob(jobId)
      setJob(j)
      if (j.state === 'done') {
        setAudioVersion((v) => v + 1)
        setVersionsKey((k) => k + 1)
        load()
      }
    }, 700)
    return () => clearInterval(timer)
  }, [jobId, load])

  // Your own audio is added as another version of the book's audio; nothing is replaced.
  async function upload(file: File) {
    setError('')
    try {
      await uploadAudio(bookId, file)
      setJob(null)
      setAudioVersion((v) => v + 1)
      setVersionsKey((k) => k + 1)
      load()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  // Syncing finds when each sentence of the text is spoken in your own recording.
  async function sync(v: AudioVersion) {
    setError('')
    setNeedsAligner(false)
    try {
      setJob(await syncAudioVersion(bookId, v.id))
    } catch (e) {
      const err = e as Error & { code?: string }
      if (err.code === 'model_not_installed') setNeedsAligner(true)
      else setError(err.message)
    }
  }

  async function cancel() {
    if (job) setJob(await cancelJob(job.id).catch(() => job))
  }

  // Generating adds a version next to what the book already has; nothing is replaced.
  async function generate() {
    try {
      setJob(await startAudio(bookId, { pause, model: choice.model || undefined, voice: choice.voice || undefined }))
      setChoice({ model: '', voice: '' }) // a choice made in the menu is for one generation only
    } catch (e) {
      const err = e as Error & { code?: string }
      if (err.code === 'model_not_installed') {
        setNeedsModel(true)
      } else {
        setError(err.message)
      }
    }
  }

  function onTime(t: number) {
    if (!book?.hasTimings) return
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

  const running = isActive(job)
  const pauseAndGenerate = (
    <>
      <label>
        Pause between sentences {pause.toFixed(1)} s
        <input type="range" min={0.2} max={2} step={0.1} value={pause} onChange={(e) => setPause(Number(e.target.value))} />
      </label>
      <span className="split">
        <button disabled={running || optionsError !== ''} onClick={() => generate()}>
          Generate audio
        </button>
        {options ? (
          <AudioOptionsMenu options={options} choice={choice} onChange={setChoice} disabled={running} />
        ) : (
          // Same size as the real button, so nothing jumps when the options arrive.
          <button className="secondary icon-button" disabled aria-label="Loading model and voice options">
            ⋯
          </button>
        )}
      </span>
      <label className="file-button">
        <input
          type="file"
          accept="audio/*,.m4b,.opus"
          disabled={running}
          onChange={(e) => {
            const f = e.target.files?.[0]
            e.target.value = ''
            if (f) upload(f)
          }}
        />
        <span className={`button secondary${running ? ' disabled' : ''}`}>Add my own audio…</span>
      </label>
    </>
  )
  return (
    <>
      <p>
        <a href="#/">← Books</a>
      </p>
      <h1>{book.title}</h1>
      <div className="book-head">
        <span className="muted">{book.language}</span>
        <a className="button" href={`#/book/${book.id}/read/${book.currentPage}`}>
          {book.currentPage > 1 ? `Continue reading · page ${book.currentPage}` : 'Read'}
        </a>
      </div>

      <section className="panel">
        <AudioVersions
          bookId={book.id}
          refreshKey={versionsKey}
          disabled={running}
          onSync={sync}
          onChanged={() => {
            setAudioVersion((v) => v + 1)
            load()
          }}
        />
        {book.hasAudio ? (
          <AudioBar bookId={book.id} language={book.language} version={audioVersion} audioRef={audio} onTime={onTime}>
            {pauseAndGenerate}
          </AudioBar>
        ) : (
          <div className="controls">
            {pauseAndGenerate}
          </div>
        )}
        {options && (
          <p className="muted audio-using">
            {book.hasAudio && <>Adds a new version; your other audio is kept. </>}
            {modelName(options, choice.model || options.defaultModel)} · {voiceName(options, choice.voice || options.defaultVoice)}
            {(choice.model || choice.voice) && (
              <>
                {' '}
                <strong>(this time only)</strong>{' '}
                <button className="link-button" onClick={() => setChoice({ model: '', voice: '' })}>
                  Use the defaults
                </button>
              </>
            )}
          </p>
        )}
        {optionsError && <p className="error">{optionsError}</p>}
        {book.hasTimings && book.audioModel && options && (
          <p className="muted">Audio made with {modelName(options, book.audioModel)}.</p>
        )}
        {job && running && (
          <div className="progress">
            {job.state === 'queued' ? (
              <span className="muted">
                Waiting for {job.queuePosition === 1 ? 'the job before it' : `${job.queuePosition! - 1} jobs before it`}…
              </span>
            ) : (
              <>
                <progress value={job.done} max={job.total || 1} />
                <span className="muted">
                  {job.kind === 'sync' ? 'Syncing with the text · ' : ''}
                  {job.done} / {job.total || '…'} sentences
                </span>
              </>
            )}
            <button className="secondary" onClick={cancel}>
              Cancel
            </button>
          </div>
        )}
        {job?.state === 'cancelled' && (
          <p className="muted">Cancelled. Sentences already voiced are kept, so starting again is quick.</p>
        )}
        {job?.state === 'error' && (
          <div className="error">
            <p>{job.error}</p>
            {job.detail && (
              <details>
                <summary>Technical details</summary>
                <code>{job.detail}</code>
              </details>
            )}
          </div>
        )}
        {needsAligner && (
          <p className="error">
            The audio sync model is not downloaded yet. <a href="#/settings">Download it in Settings</a>.
          </p>
        )}
        {needsModel && (
          <p className="error">
            The voice model is not downloaded yet. <a href="#/settings">Download it in Settings</a>.
          </p>
        )}
        {book.hasAudio && !book.hasTimings && (
          <p className="muted">Sentences can't follow this recording yet. Press “Sync with the text” and they will light up as it plays.</p>
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
