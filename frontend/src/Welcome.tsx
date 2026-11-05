import { useEffect, useState } from 'react'
import { addPredefinedLanguages, downloadModel, getLanguageTemplate, getModels, type Model } from './api'
import { formatBytes } from './format'
import { useOffline } from './offline'

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
  const [picked, setPicked] = useState<string[] | null>(null) // the starter models ticked (all of them until you change it)
  const offline = useOffline()

  useEffect(() => {
    getLanguageTemplate().then((t) => setAvailable(t.predefined), (e) => setError(e.message))
    getModels().then(setModels, () => undefined)
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
  const starters = models.filter((m) => m.badge === 'Recommended' && !m.installed)
  const ticked = picked ?? starters.map((m) => m.id)
  const total = starters.filter((m) => ticked.includes(m.id)).reduce((n, m) => n + m.sizeBytes, 0)

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
          Mac. Each is a one-time download; after that everything works without the internet.
        </p>
        {starters.length === 0 ? (
          <p>The recommended models are installed.</p>
        ) : (
          <ul className="starter-models">
            {starters.map((m) => (
              <li key={m.id}>
                <label className="inline">
                  <input
                    type="checkbox"
                    checked={ticked.includes(m.id)}
                    onChange={() => setPicked(ticked.includes(m.id) ? ticked.filter((x) => x !== m.id) : [...ticked, m.id])}
                  />{' '}
                  {m.name} <span className="muted">· {formatBytes(m.sizeBytes)}</span>
                </label>
              </li>
            ))}
          </ul>
        )}
        {offline && <p className="muted">Work offline is on, so nothing can be downloaded now (Settings → General).</p>}
        {error && <p className="error">{error}</p>}
        <p>
          {starters.length > 0 && (
            <button disabled={busy || offline || ticked.length === 0} onClick={getModelsNow}>
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
