import { SettingRow, SettingsGroup } from './SettingsKit'
import { SystemVoices } from './SystemVoices'
import { useCallback, useEffect, useState } from 'react'
import {
  canPickFolder,
  checkModel,
  deleteModel,
  downloadModel,
  getJob,
  getModels,
  getVoices,
  getPref,
  importModel,
  isActive,
  pickFolder,
  removeModelEntry,
  setPref,
  setPrefs,
  type Job,
  type Model,
  type Voice,
  getStorage,
  getLanguages,
  getTranslateSettings,
  putTranslateSettings,
  type TranslateSettings,
  type Storage as StorageInfo,
} from './api'
import { AddModel } from './AddModel'
import { useOffline } from './offline'
import { ModelList, type ModelActions } from './ModelList'
import { speechCodesUsing, speechModelFor } from './modelRows'
import { formatBytes } from './format'
import { notify } from './notices'
import { SPEECH_LANGUAGES, codeOfLanguage } from './speechLanguages'
import { Voices } from './Voices'
import { Pronunciation } from './Pronunciation'

// " · 5.8 GB" after a section title, when something of that kind is downloaded.
const size = (storage: StorageInfo | null, kind: StorageInfo['groups'][number]['kind']) => {
  const bytes = storage?.groups.find((g) => g.kind === kind)?.bytes ?? 0
  return bytes > 0 ? ` · ${formatBytes(bytes)}` : ''
}

export function Settings({ part }: { part: 'models' | 'voices' }) {
  const offline = useOffline()
  const [models, setModels] = useState<Model[] | null>(null)
  const [job, setJob] = useState<Job | null>(null)
  const [error, setError] = useState('')
  const [speed, setSpeed] = useState(0)
  const [chosen, setChosen] = useState<Record<string, string>>({})
  const [voices, setVoices] = useState<Voice[]>([])
  const [libraryCodes, setLibraryCodes] = useState<string[]>([])
  const [translation, setTranslation] = useState<TranslateSettings | null>(null)
  useEffect(() => {
    getLanguages().then((list) => setLibraryCodes(Object.keys(SPEECH_LANGUAGES).filter((c) => list.some((l) => codeOfLanguage(l.name) === c))), () => undefined)
    getTranslateSettings().then(setTranslation, () => undefined)
  }, [])
  const loadVoices = useCallback(() => getVoices().then(setVoices, () => undefined), [])
  useEffect(() => {
    loadVoices()
  }, [loadVoices])

  const [storage, setStorage] = useState<StorageInfo | null>(null)

  const load = useCallback(
    () => {
      getStorage().then(setStorage, () => undefined) // the sizes change whenever a model is downloaded or deleted
      return getModels().then(
        (list) => {
          setModels(list)
          // A download started earlier (or in another window) keeps showing its progress.
          const active = list.find((m) => m.downloadJob)
          if (active?.downloadJob) getJob(active.downloadJob).then((j) => setJob((cur) => cur ?? j))
        },
        (e) => setError(e.message),
      )
    },
    [],
  )
  useEffect(() => {
    load()
  }, [load])

  const jobId = isActive(job) ? job!.id : null
  useEffect(() => {
    if (!jobId) return
    // Speed is measured between polls and smoothed, so the time left does not jump around.
    const sample = { t: 0, done: 0, smooth: 0 }
    const timer = setInterval(async () => {
      const j = await getJob(jobId)
      const now = Date.now()
      if (sample.t && now > sample.t) {
        const instant = ((j.done - sample.done) * 1000) / (now - sample.t)
        sample.smooth = sample.smooth ? 0.7 * sample.smooth + 0.3 * instant : instant
      }
      sample.t = now
      sample.done = j.done
      setSpeed(sample.smooth)
      setJob(j)
      if (!isActive(j)) {
        load()
        if (j.state === 'done' && j.kind === 'download') notify(`${j.title ?? 'The model'} is downloaded`)
      }
    }, 700)
    return () => clearInterval(timer)
  }, [jobId, load])

  async function download(id: string) {
    setError('')
    setSpeed(0)
    try {
      setJob(await downloadModel(id))
    } catch (e) {
      setError((e as Error).message)
    }
  }

  async function importFrom(m: Model) {
    setError('')
    try {
      // The desktop app has a native folder dialog; the browser used in development asks for a path.
      const folder = canPickFolder()
        ? await pickFolder()
        : window.prompt('Path of the folder with the downloaded model files')
      if (folder) setJob(await importModel(m.id, folder))
    } catch (e) {
      setError((e as Error).message)
    }
  }

  function choose(key: string, value: string) {
    setPref(key, value)
    setChosen((cur) => ({ ...cur, [key]: value }))
  }

  async function test(m: Model) {
    setError('')
    setSpeed(0)
    try {
      setJob(await checkModel(m.id))
    } catch (e) {
      setError((e as Error).message)
    }
  }

  async function forget(m: Model) {
    if (!window.confirm(`Remove ${m.name} from the list? Its downloaded files are deleted too.`)) return
    setError('')
    try {
      await removeModelEntry(m.id)
      load()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  async function remove(m: Model) {
    if (!window.confirm(`Delete ${m.name} (${formatBytes(m.sizeBytes)})? You can download it again.`)) return
    setError('')
    try {
      await deleteModel(m.id)
      setJob(null)
      load()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  if (!models) return error ? <p className="error">{error}</p> : <p className="muted">Loading…</p>
  const busy = isActive(job)

  const codes = libraryCodes.length ? libraryCodes : Object.keys(SPEECH_LANGUAGES)
  const chosenFor = (code: string) => chosen[`model.${code}`] ?? getPref<string>(`model.${code}`, '')
  const everyone = (used: string[]): 'all' | string[] | null => (used.length === 0 ? null : used.length === codes.length ? 'all' : used)
  const actions = (kind: NonNullable<Model['kind']>): ModelActions => {
    const ofKind = models.filter((m) => (m.kind ?? 'speech') === kind)
    const base = { busy, offline, job, speed, codes, onDownload: download, onImport: importFrom, onTest: test, onDelete: remove, onForget: forget, onJob: setJob }
    if (kind === 'speech') {
      return {
        ...base,
        usedFor: (m) => everyone(speechCodesUsing(m, codes, models, chosenFor)),
        onUse: (m) => {
          const values = Object.fromEntries(codes.filter((c) => m.languages.includes(c)).map((c) => [`model.${c}`, m.id]))
          setPrefs(values)
          setChosen((cur) => ({ ...cur, ...values }))
        },
        onUseFor: (m, code) => {
          setPrefs({ [`model.${code}`]: m.id })
          setChosen((cur) => ({ ...cur, [`model.${code}`]: m.id }))
        },
      }
    }
    if (kind === 'text') {
      return {
        ...base,
        usedFor: (m) => {
          if (translation?.provider !== 'local') return null
          const used = codes.filter((c) => (translation.localModelByLanguage?.[c] ?? translation.localModel.id) === m.id)
          return everyone(used)
        },
        onUse: (m) => putTranslateSettings({ provider: 'local', localModel: m.id, allLanguages: true }).then(setTranslation, (e) => setError(e.message)),
        onUseFor: (m, code) => putTranslateSettings({ provider: 'local', localModelFor: { language: code, model: m.id } }).then(setTranslation, (e) => setError(e.message)),
      }
    }
    const first = ofKind.find((m) => m.installed && !(m.check && !m.check.ok))
    return { ...base, usedFor: (m) => (first?.id === m.id ? 'all' : null) } // one model does the whole job: nothing to switch
  }

  return (
    <>
      <h1>{part === 'models' ? 'Models' : 'Voices'}</h1>
      {error && part === 'voices' && <p className="error">{error}</p>}
      {part === 'models' && storage && storage.modelsBytes > 0 && (
        <p className="storage-summary">
          Local models use <strong>{formatBytes(storage.modelsBytes)}</strong>
          <span className="muted">
            {' '}
            · {storage.groups.filter((g) => g.bytes > 0).map((g) => `${g.label.replace(' models', '').replace(' model', '')} ${formatBytes(g.bytes)}`).join(' · ')}
          </span>{' '}
          · <a href="#/settings/storage">See Storage</a>
        </p>
      )}
      {part === 'models' && (
        <>
      <h2>Voice models{size(storage, 'speech')}</h2>
      <p className="muted">
        They make the audio of your books and say words aloud, locally. Audio generation needs one. The tick means it is used for all your languages.
      </p>
      <p className="muted mr-hint">Click a language's grade to use the model for that language only. Voices and how words are said are under <a href="#/settings/voices">Voices</a>.</p>
      {error && <p className="error">{error}</p>}
      <ModelList models={models.filter((m) => (m.kind ?? 'speech') === 'speech')} a={actions('speech')} />

      <h2>Translation models{size(storage, 'text')}</h2>
      <p className="muted">
        Translate sentences locally, offline and without limits. The tick is the one used when Translation is set to the local model. A model is loaded only while you translate.
      </p>
      <p className="muted mr-hint">Click a language's grade to use the model for that language only. The service, your key and the language to translate into are under <a href="#/settings/translation">Translation</a>.</p>
      <ModelList models={models.filter((m) => m.kind === 'text')} a={actions('text')} />

      <h2>Audio sync model{size(storage, 'aligner')}</h2>
      <p className="muted">Syncs a recording of your own with the text, so sentences light up as it plays (“Sync with the text” on a book's audio page).</p>
      <ModelList models={models.filter((m) => m.kind === 'aligner')} a={actions('aligner')} />

      <h2>Transcription model{size(storage, 'transcriber')}</h2>
      <p className="muted">Writes down what is said in a YouTube video, when you add study material, and gives automatic captions their punctuation. It runs only while a video is being transcribed.</p>
      <ModelList models={models.filter((m) => m.kind === 'transcriber')} a={actions('transcriber')} />

      <AddModel onAdded={load} />

        </>
      )}

      {part === 'voices' && (
        <>
      <Pronunciation />
      <SystemVoices />

      <SettingsGroup title="Voice per language">
        {Object.entries(SPEECH_LANGUAGES).map(([code, name]) => {
          const model = speechModelFor(code, models, chosenFor(code))
          const voice = chosen[`voice.${code}`] ?? getPref<string>(`voice.${code}`, '')
          return (
            <SettingRow key={code} label={name} info="Which voice speaks the audio of books in this language. The model that makes it is chosen under Models.">
              <span className="muted">
                {model ? model.name.replace(/\s*\(.*\)\s*$/, '') : 'No voice model yet'} · <a href="#/settings/models">change</a>
              </span>
              <select value={voice} onChange={(e) => choose(`voice.${code}`, e.target.value)} aria-label={`Voice for ${name}`}>
                <option value="">Automatic</option>
                {voices.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name}
                  </option>
                ))}
              </select>
            </SettingRow>
          )
        })}
      </SettingsGroup>
      <Voices voices={voices} onChange={loadVoices} />
        </>
      )}
    </>
  )
}
