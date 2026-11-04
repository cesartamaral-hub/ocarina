import { useEffect, useRef, useState } from 'react'
import { cancelJob, createBook, extractFromFile, extractFromUrl, getJob, getLanguages, getPref, setPref, type Extracted, type Job, type Language } from './api'

const FILE_TYPES = '.txt,.epub,.pdf,.srt,.vtt'

const isVideo = (url: string) => /(^|\/\/|\.)(youtube\.com|youtu\.be)\b/i.test(url.trim())
const isJob = (x: Extracted | Job): x is Job => 'state' in x

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

export function NewBook() {
  const [languages, setLanguages] = useState<Language[]>([])
  const [languageId, setLanguageId] = useState(getPref<number>('newBook.languageId', 0))
  const [title, setTitle] = useState('')
  const [text, setText] = useState('')
  const [sourceUri, setSourceUri] = useState('')
  const [audio, setAudio] = useState<File | null>(null)
  const [url, setUrl] = useState('')
  const [note, setNote] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [keepAudio, setKeepAudio] = useState(false)
  const [audioToken, setAudioToken] = useState<string | null>(null)
  const [video, setVideo] = useState<{ videoId: string; anchors: [number, number][] } | null>(null)
  const [watch, setWatch] = useState(true)
  const [job, setJob] = useState<Job | null>(null)
  const [needsModel, setNeedsModel] = useState(false)
  const cancelled = useRef(false)

  useEffect(() => {
    getLanguages().then(
      (list) => {
        setLanguages(list)
        setLanguageId((cur) => (list.some((l) => l.id === cur) ? cur : (list[0]?.id ?? 0)))
      },
      (e) => setError(e.message),
    )
  }, [])

  function fill(got: Extracted) {
    setTitle(got.title)
    setText(got.text)
    setSourceUri(got.sourceUri)
    setNote(got.note ?? '')
    setAudioToken(got.audioToken ?? null)
    setVideo(got.videoId && got.anchors ? { videoId: got.videoId, anchors: got.anchors } : null)
  }

  async function run(extract: () => Promise<Extracted | Job>) {
    setError('')
    setNeedsModel(false)
    setBusy(true)
    cancelled.current = false
    try {
      let got = await extract()
      if (isJob(got)) {
        // A video to transcribe takes a while: follow the job until it is done.
        let current: Job = got
        setJob(current)
        while (current.state === 'queued' || current.state === 'running') {
          await sleep(1000)
          if (cancelled.current) return
          current = await getJob(current.id)
          setJob(current)
        }
        if (current.state === 'error') throw new Error(current.error ?? 'The video could not be imported.')
        if (current.state === 'cancelled' || !current.result) return
        got = current.result
      }
      fill(got)
    } catch (e) {
      setError((e as Error).message)
      setNeedsModel((e as { code?: string }).code === 'model_not_installed')
    } finally {
      setJob(null)
      setBusy(false)
    }
  }

  async function cancelImport() {
    cancelled.current = true
    if (job) await cancelJob(job.id).catch(() => undefined)
    setJob(null)
    setBusy(false)
  }

  async function save() {
    setError('')
    setBusy(true)
    try {
      const { id } = await createBook({ title, languageId, text, sourceUri, audio, importAudio: audioToken, video: watch && video ? video : null })
      setPref('newBook.languageId', languageId)
      window.location.hash = `#/book/${id}`
    } catch (e) {
      setError((e as Error).message)
      setBusy(false)
    }
  }

  return (
    <>
      <p>
        <a href="#/">← Books</a>
      </p>
      <h1>Add study material</h1>
      <p className="muted">A book, an article, a video or a text of your own: get its text here, check it, and save it to read and study.</p>

      <section className="panel static">
        <div className="controls">
          <label>
            A file (txt, epub, pdf, srt, vtt)
            <input
              type="file"
              accept={FILE_TYPES}
              disabled={busy}
              onChange={(e) => {
                const f = e.target.files?.[0]
                if (f) run(() => extractFromFile(f))
              }}
            />
          </label>
          <label>
            A web page or a YouTube video
            <span className="row-inline">
              <input value={url} placeholder="https://" disabled={busy} onChange={(e) => setUrl(e.target.value)} />
              <button
                className="secondary"
                disabled={busy || !url.trim()}
                onClick={() => run(() => extractFromUrl(url.trim(), { languageId, keepAudio: keepAudio && isVideo(url) }))}
              >
                Get text
              </button>
            </span>
          </label>
        </div>
        {isVideo(url) && (
          <>
            <label className="keep-sound">
              <input type="checkbox" checked={keepAudio} disabled={busy} onChange={(e) => setKeepAudio(e.target.checked)} />
              Keep the video's sound as the audio of this material
            </label>
            <p className="muted source-hint">
              The captions of the video are used. Without captions, Ocarina transcribes the sound on this Mac (needs the transcription model, under{' '}
              <a href="#/settings/models">Models</a>).
            </p>
          </>
        )}
        {busy && job && (
          <div className="import-progress" role="status">
            <progress aria-label="Importing the video" />
            <span className="muted">{job.state === 'queued' ? 'Waiting for the job before it…' : (job.message ?? 'Working…')}</span>
            <button className="secondary" onClick={cancelImport}>
              Cancel
            </button>
          </div>
        )}
        <p className="muted source-hint">Or just paste or type the text below.</p>
      </section>

      <div className="form">
        <label>
          Language
          <select value={languageId} onChange={(e) => setLanguageId(Number(e.target.value))}>
            {languages.map((l) => (
              <option key={l.id} value={l.id}>
                {l.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Title
          <input value={title} maxLength={255} onChange={(e) => setTitle(e.target.value)} />
        </label>
        <label>
          Text
          <textarea rows={14} value={text} onChange={(e) => setText(e.target.value)} />
        </label>
        {note && <p className="muted">{note}</p>}
        <label>
          Source (optional)
          <input value={sourceUri} onChange={(e) => setSourceUri(e.target.value)} />
        </label>
        <label>
          Audio of your own (optional; you can also generate it afterwards)
          <input type="file" accept="audio/*,.m4b,.opus" onChange={(e) => setAudio(e.target.files?.[0] ?? null)} />
        </label>
        {audioToken && <p className="muted">The sound of the video will be saved as this material's audio.</p>}
        {video && (
          <label className="keep-sound">
            <input type="checkbox" checked={watch} onChange={(e) => setWatch(e.target.checked)} />
            Play the video in the reader, with the text following it (needs internet)
          </label>
        )}
        {error && (
          <p className="error">
            {error} {needsModel && <a href="#/settings/models">Open Models</a>}
          </p>
        )}
        <div>
          <button disabled={busy || !title.trim() || !text.trim() || !languageId} onClick={save}>
            Save material
          </button>
        </div>
      </div>
    </>
  )
}
