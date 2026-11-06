import { useEffect, useState } from 'react'
import { addVoice, deleteVoice, getJob, isActive, previewUrl, previewVoice, type Job, type Voice } from './api'
import { notify } from './notices'
import { SPEECH_LANGUAGES } from './speechLanguages'
import { SettingRow, SettingsGroup } from './SettingsKit'

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
      <SettingsGroup title="Voice samples">
        <SettingRow
          label="Preview language"
          info="Chatterbox imitates a short clip of a voice. The clip sets how the voice sounds, not how fast it speaks. Audio8 only imitates a clip when you also give the exact words spoken in it; without them it uses its own voice."
        >
          <select aria-label="Preview language" value={language} onChange={(e) => setLanguage(e.target.value)}>
            {Object.entries(SPEECH_LANGUAGES).map(([code, label]) => (
              <option key={code} value={code}>
                {label}
              </option>
            ))}
          </select>
        </SettingRow>
        {voices.map((v) => {
          const waiting = job?.voice === v.id && isActive(job.job)
          const detail = `${v.builtin ? 'Comes with Ocarina' : 'Your clip'} · ${v.seconds} s${!v.builtin ? (v.transcript ? ' · words given' : ' · no words given (Chatterbox only)') : ''}`
          return (
            <SettingRow key={v.id} label={v.name} info={detail}>
              <button className="secondary" disabled={waiting} onClick={() => preview(v.id)}>
                {waiting ? (job?.job.state === 'queued' ? 'Waiting…' : 'Speaking…') : '▶ Preview'}
              </button>
              {!v.builtin && (
                <button className="danger" onClick={() => remove(v)}>
                  Remove
                </button>
              )}
            </SettingRow>
          )
        })}
      </SettingsGroup>

      <SettingsGroup title="Add a voice sample">
        <SettingRow label="Name" info="Optional.">
          <input className="set-input" aria-label="Voice name" value={name} placeholder="e.g. Marsel" onChange={(e) => setName(e.target.value)} />
        </SettingRow>
        <SettingRow label="Words spoken in the clip" info="Optional, but needed for Audio8 to imitate the clip.">
          <textarea className="set-input" aria-label="Words spoken in the clip" rows={2} value={transcript} onChange={(e) => setTranscript(e.target.value)} />
        </SettingRow>
        <SettingRow label="Voice clip" info="10 to 20 seconds of clean speech, no music or noise. wav, mp3, flac or ogg.">
          <input
            type="file"
            accept=".wav,.mp3,.flac,.ogg,audio/*"
            aria-label="Add a voice"
            onChange={(e) => {
              const f = e.target.files?.[0]
              e.target.value = ''
              if (f) upload(f)
            }}
          />
        </SettingRow>
      </SettingsGroup>
      {error && <p className="error">{error}</p>}
    </>
  )
}
