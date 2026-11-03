import { useEffect, useState } from 'react'
import { addPredefinedLanguages, getLanguageTemplate, getModels, type Model } from './api'

// First run: choose the languages you study, then be pointed at a voice model for listening.
export function Welcome({ onFinish }: { onFinish: () => void }) {
  const [step, setStep] = useState<'languages' | 'voice'>('languages')
  const [available, setAvailable] = useState<string[]>([])
  const [chosen, setChosen] = useState<string[]>([])
  const [filter, setFilter] = useState('')
  const [withBooks, setWithBooks] = useState(true)
  const [models, setModels] = useState<Model[]>([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

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
      setStep('voice')
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const shown = available.filter((n) => n.toLowerCase().includes(filter.trim().toLowerCase()))
  const hasVoice = models.some((m) => m.kind !== 'text' && m.installed)

  if (step === 'voice') {
    return (
      <section className="welcome">
        <h1>Listening</h1>
        {hasVoice ? (
          <p>A voice model is installed, so you can make audio for any book with one click.</p>
        ) : (
          <>
            <p>
              Ocarina can read your books aloud with a voice model that runs on this Mac. It is a one-time download of a few gigabytes. Reading works
              without it.
            </p>
            <p>
              <a className="button" href="#/settings">
                Choose a voice model
              </a>
            </p>
          </>
        )}
        <p>
          <button className="secondary" onClick={onFinish}>
            {hasVoice ? 'Start reading' : 'Later, start reading'}
          </button>
        </p>
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
