import { useState } from 'react'
import { compareModels, testTranslation, type Comparison, type TestResult, type TranslateSettings } from './api'
import { NoLocalModelNotice } from './NoLocalModelNotice'
import { SettingRow, SettingsGroup } from './SettingsKit'

// Settings -> Translation: type a sentence and see what the service you chose makes of it, or what each local model makes of it.
export function TryTranslation({ s }: { s: TranslateSettings }) {
  const samples = s.samples
  const [languageId, setLanguageId] = useState<number | null>(samples[0]?.languageId ?? null)
  const [text, setText] = useState(samples[0]?.sample ?? '')
  const [touched, setTouched] = useState(false) // you typed your own: changing the language no longer swaps in a sample
  const [state, setState] = useState<{ busy: string; result?: TestResult; results?: Comparison[]; error?: string }>({ busy: '' })
  const installed = s.localModels.filter((m) => m.installed)
  const noLocal = Boolean(s.offline) && installed.length === 0
  const sampleOf = (id: number | null) => samples.find((x) => x.languageId === id)?.sample ?? ''
  const ready = languageId !== null && text.trim() !== '' && state.busy === ''

  async function run(what: 'translate' | 'compare') {
    if (languageId === null) return
    setState({ busy: what })
    try {
      if (what === 'translate') setState({ busy: '', result: await testTranslation(languageId, text) })
      else setState({ busy: '', results: (await compareModels(languageId, text)).results })
    } catch (e) {
      setState({ busy: '', error: (e as Error).message })
    }
  }

  if (samples.length === 0) return null
  const providerName = (id: string) => s.providers.find((p) => p.id === id)?.name ?? id
  const sourceName = samples.find((x) => x.languageId === languageId)?.name ?? ''
  return (
    <SettingsGroup title="Try it">
      {noLocal && (
        <p className="set-note muted">
          <NoLocalModelNotice />
        </p>
      )}
      {samples.length > 1 && (
        <SettingRow label="Language of the sentence">
          <select
            aria-label="Language of the sentence"
            value={languageId ?? ''}
            onChange={(e) => {
              const id = Number(e.target.value)
              setLanguageId(id)
              if (!touched) setText(sampleOf(id))
            }}
          >
            {samples.map((x) => (
              <option key={x.languageId} value={x.languageId}>
                {x.name}
              </option>
            ))}
          </select>
        </SettingRow>
      )}
      <SettingRow label="Sentence">
        <input
          className="set-input wide"
          aria-label="Sentence to translate"
          value={text}
          placeholder="Type a sentence"
          onChange={(e) => {
            setText(e.target.value)
            setTouched(true)
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && ready) run('translate')
          }}
        />
      </SettingRow>
      <SettingRow label="">
        <button disabled={!ready} onClick={() => run('translate')}>
          {state.busy === 'translate' ? 'Translating…' : 'Translate'}
        </button>
        {installed.length > 0 && (
          <button className="secondary" disabled={!ready} onClick={() => run('compare')} title="Translates it with every local model you have downloaded, one after the other">
            {state.busy === 'compare' ? 'Comparing…' : 'Compare local models'}
          </button>
        )}
      </SettingRow>
      <div aria-live="polite">
        {state.error && <p className="error set-note">{state.error}</p>}
        {state.result && (
          <SettingRow label="Result" info={`${sourceName} → ${state.result.targetName} · ${providerName(state.result.provider)} · ${state.result.seconds} s`}>
            <strong>{state.result.translation}</strong>
          </SettingRow>
        )}
        {state.results?.map((r) => (
          <SettingRow key={r.id} label={r.name} info={`${r.seconds} s${r.cached ? ' · saved earlier' : ''}`}>
            <span className={r.error ? 'error' : undefined}>{r.error ?? r.translation}</span>
          </SettingRow>
        ))}
      </div>
    </SettingsGroup>
  )
}
