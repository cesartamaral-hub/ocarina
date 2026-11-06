import { useEffect, useState } from 'react'
import { getTranslateSettings, translateSentence, type Translation } from '../api'
import { notify } from '../notices'
import { cardLabel, sendsTo, serviceName, targetName } from './cardWording'
import { SpeakButton } from './SpeakButton'
import { useOffline } from '../offline'

const PLAY = <path d="M4 2.5v11l9-5.5z" fill="currentColor" />
const COPY = (
  <>
    <rect x="5.5" y="5.5" width="8" height="8" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.4" />
    <path d="M3.5 10.5v-7a1.5 1.5 0 0 1 1.5-1.5h7" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
  </>
)
const OPEN = <path d="M6 3H3v10h10v-3M9 3h4v4M13 3L7.5 8.5" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />

function Tool({ label, onClick, children }: { label: string; onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" className="quiet small icon" aria-label={label} title={label} onClick={onClick}>
      <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
        {children}
      </svg>
    </button>
  )
}

async function copy(text: string) {
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    const area = document.createElement('textarea') // the web view may not allow the clipboard API: fall back to the old way
    area.value = text
    document.body.appendChild(area)
    area.select()
    document.execCommand('copy')
    area.remove()
  }
  notify('Copied')
}

// The sentence (or the text you picked) as a quote, what you can do with it, and its translation.
// Nothing is sent anywhere until you press Translate; a translation the book already has shows at once.
export function SentenceCard({
  kind,
  text,
  languageId,
  playStart,
  onPlay,
  onOpenInBrowser: openInBrowser,
  stored,
}: {
  kind: 'sentence' | 'text'
  text: string
  languageId: number
  playStart?: number
  onPlay?: (seconds: number) => void
  onOpenInBrowser?: () => void
  stored?: string // the book's own translation of exactly this text
}) {
  const onOpenInBrowser = useOffline() ? undefined : openInBrowser // a web page needs the internet
  const [result, setResult] = useState<Translation | null>(null)
  const [error, setError] = useState<{ message: string; code?: string } | null>(null)
  const [busy, setBusy] = useState(false)
  const [provider, setProvider] = useState('')
  useEffect(() => {
    getTranslateSettings().then((s) => setProvider(s.provider), () => undefined)
  }, [])

  async function run() {
    setBusy(true)
    setError(null)
    try {
      setResult(await translateSentence(languageId, text))
    } catch (e) {
      const err = e as Error & { code?: string }
      setError({ message: err.message, code: err.code })
    } finally {
      setBusy(false)
    }
  }

  const needsSettings = error && ['no_key', 'no_model', 'bad_key', 'quota', 'unsupported_language'].includes(error.code ?? '')
  const shown = result?.translation ?? stored
  return (
    <section className="sentence-card" aria-label={cardLabel(kind, text)}>
      <div className="sc-head">
        <span className="sc-label">{cardLabel(kind, text)}</span>
        <span className="sc-tools">
          {playStart !== undefined && onPlay && (
            <Tool label="Play from here" onClick={() => onPlay(playStart)}>
              {PLAY}
            </Tool>
          )}
          <SpeakButton text={text} languageId={languageId} />
          <Tool label="Copy the text" onClick={() => copy(text)}>
            {COPY}
          </Tool>
          {onOpenInBrowser && (
            <Tool label="Translate in your browser" onClick={onOpenInBrowser}>
              {OPEN}
            </Tool>
          )}
        </span>
      </div>
      <blockquote className="sc-text">{text}</blockquote>

      <div className="sc-translation" aria-live="polite" aria-busy={busy}>
        {busy ? (
          <div className="sc-skeleton" aria-label="Translating…">
            <i />
            <i />
          </div>
        ) : shown ? (
          <>
            <p className="sc-translated">{shown}</p>
            <p className="sc-meta muted">
              {result
                ? `${targetName(result.target)} · ${serviceName(result.provider)}${result.cached ? ' · saved locally' : ''}`
                : 'From the translation of this book'}
              <span className="sc-note" title="Machine translation: it may be wrong" aria-label="Machine translation: it may be wrong">
                {' '}
                ⓘ
              </span>
            </p>
          </>
        ) : (
          <>
            <button className="sc-translate" onClick={run}>
              Translate
            </button>
            {provider && <p className="sc-meta muted">{sendsTo(provider)}</p>}
          </>
        )}
        {error && (
          <p className="sc-error">
            {error.message}{' '}
            {needsSettings && <a href="#/settings/translation">Open translation settings</a>}
            {onOpenInBrowser && (
              <>
                {needsSettings ? ' · ' : ''}
                <button className="link-button" onClick={onOpenInBrowser}>
                  Translate in your browser
                </button>
              </>
            )}
          </p>
        )}
      </div>
    </section>
  )
}
