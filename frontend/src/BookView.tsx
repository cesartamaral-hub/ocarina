import { useCallback, useEffect, useRef, useState } from 'react'
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
  type Job,
} from './api'
import { AudioOptionsMenu, type AudioChoice } from './AudioOptionsMenu'

const modelName = (o: AudioOptions, id: string) => o.models.find((m) => m.id === id)?.name ?? id
const voiceName = (o: AudioOptions, id: string) => o.voices.find((v) => v.id === id)?.name ?? id

export function BookView({ bookId }: { bookId: number }) {
  const [book, setBook] = useState<BookSentences | null>(null)
  const [error, setError] = useState('')
  const [job, setJob] = useState<Job | null>(null)
  const [audioVersion, setAudioVersion] = useState(0)
  const [pause, setPause] = useState(0.5)
  const [current, setCurrent] = useState(-1)
  const [needsModel, setNeedsModel] = useState(false)
  const [options, setOptions] = useState<AudioOptions | null>(null)
  const [optionsError, setOptionsError] = useState('')
  const [choice, setChoice] = useState<AudioChoice>({ model: '', voice: '' })
  const audio = useRef<HTMLAudioElement>(null)

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
      (jobs) => setJob((cur) => cur ?? jobs.find((j) => j.kind === 'audio' && j.book_id === bookId) ?? null),
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
        load()
      }
    }, 700)
    return () => clearInterval(timer)
  }, [jobId, load])

  async function upload(file: File) {
    if (book?.hasAudio && !window.confirm('Replace the current audio with this file?')) return
    setError('')
    try {
      await uploadAudio(bookId, file)
      setJob(null)
      setAudioVersion((v) => v + 1)
      load()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  async function cancel() {
    if (job) setJob(await cancelJob(job.id).catch(() => job))
  }

  async function generate(replace = false) {
    try {
      setJob(await startAudio(bookId, { replace, pause, model: choice.model || undefined, voice: choice.voice || undefined }))
      setChoice({ model: '', voice: '' }) // a choice made in the menu is for one generation only
    } catch (e) {
      const err = e as Error & { code?: string }
      if (err.code === 'has_user_audio') {
        if (window.confirm('This book has your own audio. Replace it with generated audio?')) {
          generate(true)
        }
      } else if (err.code === 'model_not_installed') {
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
          {book?.hasAudio ? 'Regenerate audio' : 'Generate audio'}
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
        <span className={`button secondary${running ? ' disabled' : ''}`}>Use my own audio…</span>
      </label>
    </>
  )
  return (
    <>
      <p>
        <a href="#/">← Books</a>
      </p>
      <h1>{book.title}</h1>
      <p className="muted">
        {book.language} · <a href={`#/book/${book.id}/read/${book.currentPage}`}>Read</a>
      </p>

      <section className="panel">
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
        {job?.state === 'error' && <p className="error">{job.error}</p>}
        {needsModel && (
          <p className="error">
            The voice model is not downloaded yet. <a href="#/settings">Download it in Settings</a>.
          </p>
        )}
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
