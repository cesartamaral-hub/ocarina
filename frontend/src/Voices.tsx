import { useEffect, useState } from 'react'
import { addVoice, deleteVoice, getJob, isActive, previewUrl, previewVoice, type Job, type Voice } from './api'
import { notify } from './notices'
import { SPEECH_LANGUAGES } from './speechLanguages'

export function Voices({ voices, onChange }: { voices: Voice[]; onChange: () => void }) {
  const [language, setLanguage] = useState('nl')
  const [name, setName] = useState('')
  const [transcript, setTranscript] = useState('')
  const [job, setJob] = useState<{ job: Job; voice: string } | null>(null)
  const [error, setError] = useState('')

  const jobId = job && isActive(job.job) ? job.job.id : null
  useEffect(() => {
    if (!jobId) return
    const timer = setInterval(async () => {
      const j = await getJob(jobId)
      setJob((cur) => (cur ? { ...cur, job: j } : cur))
      if (j.state === 'done' && j.preview) new Audio(previewUrl(j.preview)).play().catch(() => undefined)
      if (j.state === 'error') setError(j.error ?? 'The preview failed')
    }, 600)
    return () => clearInterval(timer)
  }, [jobId])

  async function preview(voice: string) {
    setError('')
    try {
      setJob({ job: await previewVoice(voice, language), voice })
    } catch (e) {
      const err = e as Error & { code?: string }
      setError(err.code === 'model_not_installed' ? `${err.message}` : err.message)
    }
  }

  async function upload(file: File) {
    setError('')
    try {
      const v = await addVoice(file, name, transcript)
      setName('')
      setTranscript('')
      notify(`Voice "${v.name}" added`)
      onChange()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  async function remove(v: Voice) {
    if (!window.confirm(`Remove the voice "${v.name}"? Books keep the audio they already have.`)) return
    try {
      await deleteVoice(v.id)
      onChange()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  return (
    <>
      <h2>Voices</h2>
      <p className="muted">
        Chatterbox imitates a short clip of a voice. Add your own: 10 to 20 seconds of clean speech, no music or noise. The clip sets how the voice
        sounds, not how fast it speaks. Audio8 only imitates a clip when you also give the exact words spoken in it; without them it uses its own voice.
      </p>
      <label className="inline">
        Preview language
        <select value={language} onChange={(e) => setLanguage(e.target.value)}>
          {Object.entries(SPEECH_LANGUAGES).map(([code, label]) => (
            <option key={code} value={code}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <ul className="models">
        {voices.map((v) => {
          const waiting = job?.voice === v.id && isActive(job.job)
          return (
            <li key={v.id}>
              <div className="row">
                <div>
                  <div className="name">{v.name}</div>
                  <div className="muted">
                    {v.builtin ? 'Comes with Ocarina' : 'Your clip'} · {v.seconds} s
                    {!v.builtin && (v.transcript ? ' · words given' : ' · no words given (Chatterbox only)')}
                  </div>
                </div>
                <div className="actions">
                  <button className="secondary" disabled={waiting} onClick={() => preview(v.id)}>
                    {waiting ? (job?.job.state === 'queued' ? 'Waiting…' : 'Speaking…') : '▶ Preview'}
                  </button>
                  {!v.builtin && (
                    <button className="secondary" onClick={() => remove(v)}>
                      Remove
                    </button>
                  )}
                </div>
              </div>
            </li>
          )
        })}
      </ul>
      <div className="form voice-form">
        <label>
          Name (optional)
          <input value={name} placeholder="e.g. Marsel" onChange={(e) => setName(e.target.value)} />
        </label>
        <label>
          Words spoken in the clip (optional, needed for Audio8)
          <textarea rows={2} value={transcript} onChange={(e) => setTranscript(e.target.value)} />
        </label>
        <label>
          Add a voice (wav, mp3, flac or ogg)
          <input
            type="file"
            accept=".wav,.mp3,.flac,.ogg,audio/*"
            onChange={(e) => {
              const f = e.target.files?.[0]
              e.target.value = ''
              if (f) upload(f)
            }}
          />
        </label>
      </div>
      {error && <p className="error">{error}</p>}
    </>
  )
}
