import { useState } from 'react'
import { AlignPicker } from './AlignPicker'
import { getPref, setPref } from './api'
import { appearance, saveAppearance, type Theme } from './appearanceSettings'
import { HOVER_DELAYS, HOVER_PREFS } from './reader/useHoverCard'
import { RadioCards, type CardOption } from './RadioCards'
import { useTypography } from './useTypography'
import { FONTS, LIMITS, PRESETS, WEIGHTS, matchingPreset, spacingLabel, stepSize, widthLabel, type FontKey, type Typography } from './typography'

// A tiny page in the colours of a theme: a title bar, lines of text and a few coloured words.
function MiniPage({ palette }: { palette: 'light' | 'dark' }) {
  return (
    <span className={`mini-page pal-${palette}`} aria-hidden="true">
      <i className="bar" />
      <i className="line" style={{ width: '88%' }} />
      <i className="line">
        <b className="s1" />
        <b className="s4" />
      </i>
      <i className="line" style={{ width: '70%' }}>
        <b className="s0" />
      </i>
    </span>
  )
}

const THEMES: CardOption<Theme>[] = [
  {
    value: 'system',
    label: 'Match my Mac',
    hint: 'Light by day, dark at night',
    preview: (
      <span className="mini-split" aria-hidden="true">
        <MiniPage palette="light" />
        <MiniPage palette="dark" />
      </span>
    ),
  },
  { value: 'light', label: 'Light', hint: 'Always light', preview: <MiniPage palette="light" /> },
  { value: 'dark', label: 'Dark', hint: 'Always dark', preview: <MiniPage palette="dark" /> },
]

// A slider with its name and current value above it, so both are read together.
function Slider({ label, text, value, min, max, step, onChange }: { label: string; text: string; value: number; min: number; max: number; step: number; onChange: (v: number) => void }) {
  return (
    <label className="ap-slider">
      <span className="ap-slider-head">
        <span>{label}</span>
        <output>{text}</output>
      </span>
      <input type="range" min={min} max={max} step={step} value={value} aria-valuetext={text} onChange={(e) => onChange(Number(e.target.value))} />
    </label>
  )
}

// What the text looks like with the current settings, including the colours words have in the reader.
function Preview() {
  return (
    <article className="appearance-sample" aria-label="Preview of the reading text">
      <p lang="nl">
        Elke <span className="w s1">ochtend</span> sta ik <span className="w s3">vroeg</span> op, ik <span className="w s4">drink</span> koffie en ik{' '}
        <span className="w s0">fiets</span> naar mijn werk. Daarna lees ik de krant en <span className="w s2">bereid</span> ik het ontbijt voor.
      </p>
      <p lang="pl">
        Każdego <span className="w s0">ranka</span> <span className="w s5">wstaję</span> wcześnie i <span className="w s2">piję</span> kawę. Potem idę do pracy, a wieczorem czytam
        książkę.
      </p>
      <p lang="fr">
        Chaque <span className="w s4">matin</span>, je <span className="w s5">me lève</span> tôt. Je <span className="w s1">prends</span> mon café et je pars travailler.
      </p>
    </article>
  )
}

export function Appearance() {
  const [theme, setTheme] = useState<Theme>(() => appearance().theme)
  const [t, change] = useTypography()
  const [hoverOn, setHoverOn] = useState(() => getPref<boolean>(HOVER_PREFS.enabled, true))
  const [hoverDelay, setHoverDelay] = useState(() => getPref<number>(HOVER_PREFS.delay, 350))
  const chooseTheme = (next: Theme) => {
    saveAppearance({ theme: next })
    setTheme(next)
  }
  const preset = matchingPreset(t)

  const fonts: CardOption<FontKey>[] = Object.entries(FONTS).map(([key, f]) => ({
    value: key as FontKey,
    label: f.label,
    preview: (
      <span className="font-sample" style={{ fontFamily: f.stack }} aria-hidden="true">
        Aa
      </span>
    ),
  }))
  const presets: CardOption<string>[] = PRESETS.map((p) => ({ value: p.id, label: p.label, hint: p.hint }))

  return (
    <>
      <h1>Appearance</h1>
      <div className="ap-grid">
        <div className="ap-controls">
          <section className="ap-card">
            <h2>Theme</h2>
            <RadioCards name="theme" label="Theme" value={theme} options={THEMES} onChange={chooseTheme} className="three" />
          </section>

          <section className="ap-card">
            <h2>Reading text</h2>
            <h3>Start from</h3>
            <RadioCards
              name="preset"
              label="Preset"
              value={preset}
              options={presets}
              onChange={(id) => change(PRESETS.find((p) => p.id === id)!.values)}
              className="four plain"
            />
            {preset === null && <p className="muted ap-note">Your own settings. Pick a preset to start over from one.</p>}

            <h3>Font</h3>
            <RadioCards name="font" label="Font" value={t.font} options={fonts} onChange={(font) => change({ font })} className="four" />

            <h3>Size and spacing</h3>
            <div className="ap-size">
              <button type="button" className="secondary icon" aria-label="Smaller text" disabled={t.size <= LIMITS.size.min} onClick={() => change({ size: stepSize(t.size, -1) })}>
                A−
              </button>
              <Slider label="Text size" text={`${t.size} px`} value={t.size} min={LIMITS.size.min} max={LIMITS.size.max} step={LIMITS.size.step} onChange={(size) => change({ size })} />
              <button type="button" className="secondary icon" aria-label="Larger text" disabled={t.size >= LIMITS.size.max} onClick={() => change({ size: stepSize(t.size, 1) })}>
                A+
              </button>
            </div>
            <Slider label="Line length" text={widthLabel(t.width)} value={t.width} min={LIMITS.width.min} max={LIMITS.width.max} step={LIMITS.width.step} onChange={(width) => change({ width })} />
            <Slider label="Line spacing" text={`${t.line.toFixed(1)}×`} value={t.line} min={LIMITS.line.min} max={LIMITS.line.max} step={LIMITS.line.step} onChange={(line) => change({ line })} />

            <h3>Alignment</h3>
            <AlignPicker value={t.align} onChange={(align) => change({ align })} />
            {t.align === 'justify' && <p className="muted ap-note">Justified text may hyphenate long words.</p>}

            <details className="ap-fine">
              <summary>Fine tuning</summary>
              <label className="ap-field">
                <span>Weight</span>
                <select value={t.weight} onChange={(e) => change({ weight: Number(e.target.value) } as Partial<Typography>)}>
                  {WEIGHTS.map((w) => (
                    <option key={w.value} value={w.value}>
                      {w.label}
                    </option>
                  ))}
                </select>
              </label>
              <Slider label="Letter spacing" text={spacingLabel(t.letter, LIMITS.letter)} value={t.letter} min={LIMITS.letter.min} max={LIMITS.letter.max} step={LIMITS.letter.step} onChange={(letter) => change({ letter })} />
              <Slider label="Word spacing" text={spacingLabel(t.word, LIMITS.word)} value={t.word} min={LIMITS.word.min} max={LIMITS.word.max} step={LIMITS.word.step} onChange={(word) => change({ word })} />
            </details>

            <div className="ap-reset">
              <button type="button" className="secondary" onClick={() => change('reset')} disabled={preset === 'comfortable'}>
                Back to the standard text
              </button>
            </div>
          </section>

          <section className="ap-card">
            <h2>Hovering over words</h2>
            <label className="ap-check">
              <input
                type="checkbox"
                checked={hoverOn}
                onChange={(e) => {
                  setHoverOn(e.target.checked)
                  setPref(HOVER_PREFS.enabled, e.target.checked)
                }}
              />
              Show a word's meaning when the pointer rests on it
            </label>
            <label className="ap-field">
              <span>Wait first</span>
              <select
                value={hoverDelay}
                disabled={!hoverOn}
                onChange={(e) => {
                  setHoverDelay(Number(e.target.value))
                  setPref(HOVER_PREFS.delay, Number(e.target.value))
                }}
              >
                {HOVER_DELAYS.map((d) => (
                  <option key={d.ms} value={d.ms}>
                    {d.label}
                  </option>
                ))}
              </select>
            </label>
            <p className="muted ap-note">Your own translation first; if there is none, the first meaning from Wiktionary (needs a connection).</p>
          </section>
        </div>

        <aside className="ap-preview" aria-label="Preview">
          <h2>Preview</h2>
          <Preview />
          <p className="muted ap-note">The same settings apply while you read. You can also change them there with the “Aa” button.</p>
        </aside>
      </div>
    </>
  )
}
