import { useEffect, useState } from 'react'
import { downloadModel, getConnection, getDiskSpace, getModels, type Connection, type DiskSpace, type LanguageSupport, type Model } from './api'
import { DownloadStatus } from './DownloadStatus'
import { AddLanguages } from './AddLanguages'
import { formatBytes } from './format'
import { useOffline } from './offline'
import { featureOf } from './modelPurpose'
import { autoTicked, relevantModels, sizeOf } from './welcomeModels'
import { SettingRow, SettingsGroup, Toggle } from './SettingsKit'

// First run: choose the languages you study, then the starter models to download (voice, translation, audio sync).
export function Welcome({ onFinish }: { onFinish: () => void }) {
  const [step, setStep] = useState<'languages' | 'models'>('languages')
  const [chosen, setChosen] = useState<string[]>([])
  const [support, setSupport] = useState<Record<string, LanguageSupport>>({})
  const [models, setModels] = useState<Model[]>([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [space, setSpace] = useState<DiskSpace | null>(null)
  const [connection, setConnection] = useState<Connection | null>(null)
  const [queued, setQueued] = useState<string[] | null>(null) // the models whose download was started here
  const [picked, setPicked] = useState<string[] | null>(null) // the starter models ticked (all of them until you change it)
  const offline = useOffline()

  useEffect(() => {
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

  const codes = chosen.map((n) => support[n]?.code).filter((c): c is string => Boolean(c)) // the codes of the languages you picked
  const recommended = relevantModels(models, codes) // only what can help them
  const todo = recommended.filter((m) => !m.installed) // what can still be downloaded here
  const online = !offline && connection?.online !== false
  const ticked = picked ?? autoTicked(todo, online, space) // the translation model is ticked for you when it can help, you are online and it fits
  const total = sizeOf(todo.filter((m) => ticked.includes(m.id)))
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
    const toggle = (id: string) => setPicked(ticked.includes(id) ? ticked.filter((x) => x !== id) : [...ticked, id])
    return (
      <section className="welcome">
        <h1>Get ready</h1>
        <p className="muted">You can start reading now. These optional downloads add features and then work offline.</p>
        {recommended.length > 0 ? (
          <SettingsGroup title="Optional downloads">
            {recommended.map((m) => {
              const feature = featureOf(m)
              return (
                <SettingRow key={m.id} label={feature.title} hint={feature.line} info={`${m.name}. ${m.description}${m.license === 'gemma' ? ' Made by Google under the Gemma Terms of Use (ai.google.dev/gemma/terms).' : ''}`}>
                  {queued?.includes(m.id) ? (
                    <DownloadStatus model={m} onRetry={() => downloadModel(m.id).then(() => getModels().then(setModels), (e) => setError(e.message))} />
                  ) : m.installed ? (
                    <span className="ready-ok">✓ installed</span>
                  ) : (
                    <>
                      <span className="muted">{formatBytes(m.sizeBytes)}</span>
                      <Toggle label={feature.title} checked={ticked.includes(m.id)} disabled={queued !== null} onChange={() => toggle(m.id)} />
                    </>
                  )}
                </SettingRow>
              )
            })}
          </SettingsGroup>
        ) : (
          <p className="muted">Nothing needs downloading for your languages.</p>
        )}
        <div className="welcome-notes" aria-live="polite">
          {offline && <p className="muted">Work offline is on, so nothing can be downloaded now (Settings → General).</p>}
          {!offline && connection?.online === false && (
            <p className="muted">
              No internet connection found, so downloads wait. You can add these later under Settings → Models.{' '}
              <button className="link-button" onClick={checkConnection}>
                Check again
              </button>
            </p>
          )}
          {missing > 0 && <p className="error">Not enough free space: about {formatBytes(missing)} more is needed (Ocarina keeps {formatBytes(space!.marginBytes)} free). Untick a download or free some space.</p>}
          {error && <p className="error">{error}</p>}
        </div>
        <div className="welcome-actions">
          {queued ? (
            <button onClick={onFinish}>Start reading</button>
          ) : ticked.length > 0 ? (
            <>
              <button disabled={busy || !online || missing > 0} onClick={getModelsNow}>
                Download {formatBytes(total)}
              </button>
              <button className="quiet" onClick={onFinish}>
                Skip for now
              </button>
            </>
          ) : (
            <button onClick={onFinish}>Continue</button>
          )}
        </div>
        <p className="muted">{queued ? 'Downloads continue in the background, also after you start reading.' : 'You can add or change these any time under Settings → Models.'}</p>
      </section>
    )
  }

  return (
    <section className="welcome">
      <h1>Welcome to Ocarina</h1>
      <p>Which languages do you study? You can add more later under Languages.</p>
      <AddLanguages
        onAdded={(names, rows) => {
          setChosen(names)
          setSupport(rows)
          setStep('models')
        }}
      />
    </section>
  )
}
