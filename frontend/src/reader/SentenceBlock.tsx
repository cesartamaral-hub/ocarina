import { useState } from 'react'
import { translateSentence, type Translation } from '../api'

const PROVIDER_NAMES: Record<string, string> = { local: 'On this Mac', mymemory: 'MyMemory', deepl: 'DeepL' }

// The sentence the word is in, with a translation on request. Nothing is sent anywhere until you press Translate
// (the sentence goes to the service chosen in Settings). Keyed by the sentence, so a new sentence starts clean.
export function SentenceBlock({
  languageId,
  text,
  playStart,
  onPlay,
  onOpenInBrowser,
}: {
  languageId: number
  text: string
  playStart?: number
  onPlay: (seconds: number) => void
  onOpenInBrowser?: () => void
}) {
  const [result, setResult] = useState<Translation | null>(null)
  const [error, setError] = useState<{ message: string; code?: string } | null>(null)
  const [busy, setBusy] = useState(false)

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
  return (
    <section className="sentence-block" aria-label="The sentence">
      <p className="sentence-text">{text}</p>
      <div className="sentence-actions">
        <button className="secondary" disabled={busy} onClick={run}>
          {busy ? 'Translating…' : result ? 'Translate again' : 'Translate sentence'}
        </button>
        {playStart !== undefined && (
          <button className="secondary" onClick={() => onPlay(playStart)}>
            ▶ Play sentence
          </button>
        )}
      </div>
      <div aria-live="polite">
        {result && (
          <p className="sentence-translation">
            {result.translation}
            <span className="muted">
              {' '}
              {PROVIDER_NAMES[result.provider] ?? result.provider}
              {result.cached ? ' · saved' : ''} · machine translation, may be wrong
            </span>
          </p>
        )}
        {error && (
          <p className="muted">
            {error.message}{' '}
            {needsSettings && <a href="#/translation">Open translation settings</a>}
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
