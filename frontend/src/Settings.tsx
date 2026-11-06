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
  getLanguageSupport,
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
import { SPEECH_LANGUAGES } from './speechLanguages'
import { Voices } from './Voices'
import { Pronunciation } from './Pronunciation'

// "5.8 GB" beside a group's title, when something of that kind is downloaded.
const size = (storage: StorageInfo | null, kind: StorageInfo['groups'][number]['kind']) => {
  const bytes = storage?.groups.find((g) => g.kind === kind)?.bytes ?? 0
  return bytes > 0 ? formatBytes(bytes) : null
}

// The voice engine's name in a list: the Mac voice, or the better voice without its technical tail.
const engineName = (m: Model) => (m.builtin ? 'Mac voice' : m.name.replace(/\s*\(.*\)\s*$/, ''))

export function Settings({ part }: { part: 'models' | 'voices' }) {
  const offline = useOffline()
  const [models, setModels] = useState<Model[] | null>(null)
  const [job, setJob] = useState<Job | null>(null)
  const [error, setError] = useState('')
  const [speed, setSpeed] = useState(0)
  const [chosen, setChosen] = useState<Record<string, string>>({})
  const [voices, setVoices] = useState<Voice[]>([])
  const [libraryCodes, setLibraryCodes] = useState<string[]>([])
  const [libraryNames, setLibraryNames] = useState<Record<string, string>>({})
  const [translation, setTranslation] = useState<TranslateSettings | null>(null)
  useEffect(() => {
    getLanguageSupport().then(
      (rows) => {
        const known = rows.filter((r) => r.code)
        setLibraryCodes([...new Set(known.map((r) => r.code as string))])
        setLibraryNames(Object.fromEntries(known.map((r) => [r.code as string, r.language])))
      },
      () => undefined,
    )
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
  const actions = (kind: NonNullable<Model['kind']>): ModelActions => {
    const ofKind = models.filter((m) => (m.kind ?? 'speech') === kind)
    const base = { busy, offline, job, speed, codes: libraryCodes, names: libraryNames, onDownload: download, onImport: importFrom, onTest: test, onDelete: remove, onForget: forget, onJob: setJob }
    if (kind === 'speech') {
      return {
        ...base,
        inUse: (m) => speechCodesUsing(m, codes, models, chosenFor).length > 0,
        onUse: (m) => {
          const values = Object.fromEntries(codes.filter((c) => m.languages.includes(c)).map((c) => [`model.${c}`, m.id]))
          setPrefs(values)
          setChosen((cur) => ({ ...cur, ...values }))
        },
      }
    }
    if (kind === 'text') {
      return {
        ...base,
        inUse: (m) => translation?.provider === 'local' && translation.localModel.id === m.id,
        onUse: (m) => putTranslateSettings({ provider: 'local', localModel: m.id }).then(setTranslation, (e) => setError(e.message)),
      }
    }
    const first = ofKind.find((m) => m.installed && !(m.check && !m.check.ok))
    return { ...base, inUse: (m) => first?.id === m.id } // one model does the whole job: nothing to switch
  }

  return (
    <>
      <h1>{part === 'models' ? 'Models' : 'Voices'}</h1>
      {error && part === 'voices' && <p className="error">{error}</p>}
      {part === 'models' && storage && storage.modelsBytes > 0 && (
        <p className="models-caption muted">
          Downloaded models use <strong>{formatBytes(storage.modelsBytes)}</strong> · <a href="#/settings/storage">See Storage</a>
        </p>
      )}
      {part === 'models' && (
        <>
          {error && <p className="error">{error}</p>}
          <SettingsGroup
            title="Translation"
            aside={size(storage, 'text')}
            description={
              <>
                Translate sentences locally, offline and without limits. A model loads only while you translate. The service, your key and the language to translate into are under <a href="#/settings/translation">Translation</a>.
              </>
            }
          >
            <ModelList models={models.filter((m) => m.kind === 'text')} a={actions('text')} />
          </SettingsGroup>

          <SettingsGroup
            title="Better voice"
            aside={size(storage, 'speech')}
            description={
              <>
                An optional, more natural voice for your books and for words said aloud, made locally. The Mac voice needs no download: pick between them under <a href="#/settings/voices">Voices</a>.
              </>
            }
          >
            <ModelList models={models.filter((m) => (m.kind ?? 'speech') === 'speech' && !m.builtin)} a={actions('speech')} />
          </SettingsGroup>

          <SettingsGroup title="Audio sync" aside={size(storage, 'aligner')} description="Syncs a recording of your own with the text, so sentences light up as it plays (“Sync with the text” on a book's audio page).">
            <ModelList models={models.filter((m) => m.kind === 'aligner')} a={actions('aligner')} />
          </SettingsGroup>

          <SettingsGroup title="Transcription" aside={size(storage, 'transcriber')} description="Writes down what is said in a YouTube video when you add study material, and gives automatic captions their punctuation. It runs only while a video is being transcribed.">
            <ModelList models={models.filter((m) => m.kind === 'transcriber')} a={actions('transcriber')} />
          </SettingsGroup>

          <AddModel onAdded={load} />
        </>
      )}

      {part === 'voices' && (
        <>
      <Pronunciation />
      <SystemVoices />

      <SettingsGroup title="Voice per language">
        {Object.entries(SPEECH_LANGUAGES).map(([code, name]) => {
          const engines = models.filter((m) => (m.kind ?? 'speech') === 'speech' && m.installed && !(m.check && !m.check.ok) && (m.builtin || m.languages.includes(code)))
          const asked = chosenFor(code)
          const auto = speechModelFor(code, models, '')
          const voice = chosen[`voice.${code}`] ?? getPref<string>(`voice.${code}`, '')
          return (
            <SettingRow key={code} label={name} info="The voice engine and the voice that speak the audio of books in this language. Automatic uses the better voice once it is downloaded, else the Mac voice.">
              <select value={engines.some((m) => m.id === asked) ? asked : ''} onChange={(e) => choose(`model.${code}`, e.target.value)} aria-label={`Voice engine for ${name}`}>
                <option value="">{auto ? `Automatic · ${engineName(auto)}` : 'Automatic'}</option>
                {engines.map((m) => (
                  <option key={m.id} value={m.id}>
                    {engineName(m)}
                  </option>
                ))}
              </select>
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
