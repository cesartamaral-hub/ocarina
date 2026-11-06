import { useEffect, useState } from 'react'
import { addPredefinedLanguages, downloadModel, getDiskSpace, getLanguageTemplate, getModels, type DiskSpace, type Model } from './api'
import { formatBytes } from './format'
import { useOffline } from './offline'
import { purposeOf } from './modelPurpose'

// First run: choose the languages you study, then the starter models to download (voice, translation, audio sync).
export function Welcome({ onFinish }: { onFinish: () => void }) {
  const [step, setStep] = useState<'languages' | 'models'>('languages')
  const [available, setAvailable] = useState<string[]>([])
  const [chosen, setChosen] = useState<string[]>([])
  const [filter, setFilter] = useState('')
  const [withBooks, setWithBooks] = useState(true)
  const [models, setModels] = useState<Model[]>([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [space, setSpace] = useState<DiskSpace | null>(null)
  const [picked, setPicked] = useState<string[] | null>(null) // the starter models ticked (all of them until you change it)
  const offline = useOffline()

  useEffect(() => {
    getLanguageTemplate().then((t) => setAvailable(t.predefined), (e) => setError(e.message))
    getModels().then(setModels, () => undefined)
    getDiskSpace().then(setSpace, () => undefined)
  }, [])

  const toggle = (name: string) => setChosen((cur) => (cur.includes(name) ? cur.filter((n) => n !== name) : [...cur, name]))

  async function add() {
    setError('')
    setBusy(true)
    try {
      await addPredefinedLanguages(chosen, withBooks)
      setStep('models')
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const shown = available.filter((n) => n.toLowerCase().includes(filter.trim().toLowerCase()))
  const recommended = models.filter((m) => m.badge === 'Recommended')
  const starters = recommended.filter((m) => !m.installed) // what can still be downloaded here
  const ticked = picked ?? starters.filter((m) => m.starter).map((m) => m.id) // the optional ones start unticked
  const total = starters.filter((m) => ticked.includes(m.id)).reduce((n, m) => n + m.sizeBytes, 0)
  const groups = [
    { title: 'Recommended to start', note: 'Reading works without them; these add listening and translation.', list: recommended.filter((m) => m.starter) },
    { title: 'Only if you need it', note: 'Each is for one feature. You can add them later under Settings → Models.', list: recommended.filter((m) => !m.starter) },
  ].filter((g) => g.list.length > 0)

  const missing = space ? Math.max(0, total + space.queuedBytes + space.marginBytes - space.freeBytes) : 0 // bytes short, with the margin the app keeps free

  async function getModelsNow() {
    setError('')
    setBusy(true)
    try {
      for (const id of ticked) await downloadModel(id) // they download one after another; the chip at the top shows how far
      onFinish()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  if (step === 'models') {
    return (
      <section className="welcome">
        <h1>Get ready</h1>
        <p>
          Dictionaries for your languages are on this Mac already. For listening, translating sentences and syncing audio to text, Ocarina uses models that run on this
          Mac. Each is a one-time download; after that everything works without the internet. Downloads continue in the background: reading works at once, and listening, translation and sync turn on as each model finishes.
        </p>
        {groups.map((g) => (
          <div key={g.title}>
            <h2>{g.title}</h2>
            <p className="muted">{g.note}</p>
            <ul className="starter-models">
              {g.list.map((m) => (
                <li key={m.id}>
                  {m.installed ? (
                    <span>
                      ✓ {m.name} <span className="muted">· installed</span>
                    </span>
                  ) : (
                    <label className="inline">
                      <input
                        type="checkbox"
                        checked={ticked.includes(m.id)}
                        onChange={() => setPicked(ticked.includes(m.id) ? ticked.filter((x) => x !== m.id) : [...ticked, m.id])}
                      />{' '}
                      {m.name} <span className="muted">· {formatBytes(m.sizeBytes)}</span>
                    </label>
                  )}
                  <div className="muted starter-purpose">For {purposeOf(m).charAt(0).toLowerCase() + purposeOf(m).slice(1)}</div>
                </li>
              ))}
            </ul>
          </div>
        ))}
        {starters.length === 0 && <p>The recommended models are installed.</p>}
        {space && <p className="muted">{formatBytes(space.freeBytes)} free on this Mac.</p>}
        {missing > 0 && (
          <p className="error">
            Not enough free space: about {formatBytes(missing)} more is needed (Ocarina keeps {formatBytes(space!.marginBytes)} free). Untick a model or free some space.
          </p>
        )}
        {offline && <p className="muted">Work offline is on, so nothing can be downloaded now (Settings → General).</p>}
        {error && <p className="error">{error}</p>}
        <p>
          {starters.length > 0 && (
            <button disabled={busy || offline || ticked.length === 0 || missing > 0} onClick={getModelsNow}>
              {ticked.length === 0 ? 'Choose a model' : `Download ${formatBytes(total)} and start reading`}
            </button>
          )}{' '}
          <button className="secondary" onClick={onFinish}>
            {starters.length > 0 ? 'Later, start reading' : 'Start reading'}
          </button>
        </p>
        <p className="muted">You can add or change models any time under Settings → Models. Reading works without them.</p>
      </section>
    )
  }

  return (
    <section className="welcome">
      <h1>Welcome to Ocarina</h1>
      <p>Which languages do you study? You can add more later under Languages.</p>
      <label>
        Find a language
        <input value={filter} placeholder="Type to filter" onChange={(e) => setFilter(e.target.value)} />
      </label>
      <ul className="language-choices">
        {shown.map((name) => (
          <li key={name}>
            <label className="inline">
              <input type="checkbox" checked={chosen.includes(name)} onChange={() => toggle(name)} /> {name}
            </label>
          </li>
        ))}
      </ul>
      <label className="inline">
        <input type="checkbox" checked={withBooks} onChange={(e) => setWithBooks(e.target.checked)} /> Also add the sample stories
      </label>
      {error && <p className="error">{error}</p>}
      <p>
        <button disabled={busy || chosen.length === 0} onClick={add}>
          {chosen.length === 0 ? 'Choose a language' : `Add ${chosen.length} ${chosen.length === 1 ? 'language' : 'languages'}`}
        </button>
      </p>
    </section>
  )
}
