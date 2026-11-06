import { useEffect, useState } from 'react'
import { addPredefinedLanguages, downloadModel, getConnection, getDiskSpace, getLanguageSupport, getLanguageTemplate, getModels, type Connection, type DiskSpace, type LanguageSupport, type Model } from './api'
import { DownloadStatus } from './DownloadStatus'
import { LanguagePicker } from './LanguagePicker'
import { formatBytes } from './format'
import { useOffline } from './offline'
import { purposeOf } from './modelPurpose'

// First run: choose the languages you study, then the starter models to download (voice, translation, audio sync).
export function Welcome({ onFinish }: { onFinish: () => void }) {
  const [step, setStep] = useState<'languages' | 'models'>('languages')
  const [available, setAvailable] = useState<string[]>([])
  const [chosen, setChosen] = useState<string[]>([])
  const [support, setSupport] = useState<Record<string, LanguageSupport>>({})
  const [withBooks, setWithBooks] = useState(true)
  const [models, setModels] = useState<Model[]>([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [space, setSpace] = useState<DiskSpace | null>(null)
  const [connection, setConnection] = useState<Connection | null>(null)
  const [queued, setQueued] = useState<string[] | null>(null) // the models whose download was started here
  const [picked, setPicked] = useState<string[] | null>(null) // the starter models ticked (all of them until you change it)
  const offline = useOffline()

  useEffect(() => {
    getLanguageTemplate().then(
      (t) => {
        setAvailable(t.predefined)
        getLanguageSupport(t.predefined).then((rows) => setSupport(Object.fromEntries(rows.map((r) => [r.language, r]))), () => undefined)
      },
      (e) => setError(e.message),
    )
    getModels().then(setModels, () => undefined)
    getDiskSpace().then(setSpace, () => undefined)
  }, [])
  const checkConnection = () => getConnection().then(setConnection, () => undefined)
  useEffect(() => {
    if (step === 'models') checkConnection()
  }, [step])
  useEffect(() => {
    if (!queued) return
    const timer = window.setInterval(() => getModels().then(setModels, () => undefined), 1500)
    return () => window.clearInterval(timer)
  }, [queued])

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

  const codes = chosen.map((n) => support[n]?.code).filter((c): c is string => Boolean(c)) // the codes of the languages you picked
  const recommended = models.filter((m) => m.badge === 'Recommended' && (codes.length === 0 || m.languages.some((c) => codes.includes(c)))) // only what can help them
  const starters = recommended.filter((m) => !m.installed) // what can still be downloaded here
  const ticked = picked ?? starters.filter((m) => m.starter).map((m) => m.id) // the optional ones start unticked
  const total = starters.filter((m) => ticked.includes(m.id)).reduce((n, m) => n + m.sizeBytes, 0)
  const groups = [
    { title: 'Recommended to start', note: 'Reading and listening work without these; this adds translation of sentences on this Mac.', list: recommended.filter((m) => m.starter) },
    { title: 'Only if you want it', note: 'Books are read by the Mac voice by default; the better voice, audio sync and video transcription are optional. You can add them later under Settings → Models.', list: recommended.filter((m) => !m.starter) },
  ].filter((g) => g.list.length > 0)

  const missing = space ? Math.max(0, total + space.queuedBytes + space.marginBytes - space.freeBytes) : 0 // bytes short, with the margin the app keeps free

  async function getModelsNow() {
    setError('')
    setBusy(true)
    try {
      for (const id of ticked) await downloadModel(id) // they download one after another; the chip at the top shows how far too
      setQueued(ticked)
      setModels(await getModels())
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
          Dictionaries for your languages are already installed, and books are read aloud by the voice built into your Mac, so you can start right now. Optional models run
          locally and add more: each is a one-time download, and after that it works without the internet. Downloads continue in the background, so reading works at once.
        </p>
        {groups.map((g) => (
          <div key={g.title}>
            <h2>{g.title}</h2>
            <p className="muted">{g.note}</p>
            <ul className="starter-models">
              {g.list.map((m) => (
                <li key={m.id}>
                  {m.installed && !queued?.includes(m.id) ? (
                    <span>
                      ✓ {m.name} <span className="muted">· installed</span>
                    </span>
                  ) : queued?.includes(m.id) ? (
                    <span>
                      {m.name}{' '}
                      <DownloadStatus model={m} onRetry={() => downloadModel(m.id).then(() => getModels().then(setModels), (e) => setError(e.message))} />
                    </span>
                  ) : (
                    <label className="inline">
                      <input
                        type="checkbox"
                        disabled={queued !== null}
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
        {!offline && connection && !connection.online && (
          <p className="error">
            No internet connection found, so models cannot be downloaded now. You can start reading and download them later under Settings → Models (there you can also import a model from a folder).{' '}
            <button className="secondary" onClick={checkConnection}>
              Check again
            </button>
          </p>
        )}
        {error && <p className="error">{error}</p>}
        <p>
          {queued ? (
            <button onClick={onFinish}>Start reading</button>
          ) : (
            <>
              {starters.length > 0 && (
                <button disabled={busy || offline || connection?.online === false || ticked.length === 0 || missing > 0} onClick={getModelsNow}>
                  {ticked.length === 0 ? 'Choose a model' : `Download ${formatBytes(total)}`}
                </button>
              )}{' '}
              <button className="secondary" onClick={onFinish}>
                {starters.length > 0 ? 'Later, start reading' : 'Start reading'}
              </button>
            </>
          )}
        </p>
        {queued && <p className="muted">Downloads continue in the background, also after you start reading. Progress shows at the top of the app.</p>}
        <p className="muted">You can add or change models any time under Settings → Models. Reading works without them.</p>
      </section>
    )
  }

  return (
    <section className="welcome">
      <h1>Welcome to Ocarina</h1>
      <p>Which languages do you study? You can add more later under Languages.</p>
      <LanguagePicker available={available} chosen={chosen} support={support} onChange={setChosen} />
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
