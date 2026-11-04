import { useState } from 'react'
import { saveTypography, typography } from './appearanceSettings'
import {
  ALIGNMENTS,
  FONTS,
  LIMITS,
  WEIGHTS,
  spacingLabel,
  stepSize,
  widthLabel,
  type Align,
  type FontKey,
  type Typography,
} from './typography'

type Numeric = 'width' | 'line' | 'letter' | 'word'

// The text controls, shared by the "Aa" popover in the reader and the Appearance page. Changes apply at once.
export function TypographyControls() {
  const [t, setT] = useState<Typography>(typography)
  const change = (patch: Partial<Typography> | 'reset') => setT(saveTypography(patch))
  const slider = (key: Numeric, label: string, text: string) => (
    <label className="tc-row">
      <span>{label}</span>
      <input
        type="range"
        min={LIMITS[key].min}
        max={LIMITS[key].max}
        step={LIMITS[key].step}
        value={t[key]}
        aria-valuetext={text}
        onChange={(e) => change({ [key]: Number(e.target.value) })}
      />
      <output>{text}</output>
    </label>
  )
  return (
    <div className="typography-controls">
      <div className="tc-row">
        <span id="tc-size">Text size</span>
        <div className="tc-size" role="group" aria-labelledby="tc-size">
          <button type="button" className="secondary" aria-label="Smaller text" disabled={t.size <= LIMITS.size.min} onClick={() => change({ size: stepSize(t.size, -1) })}>
            A−
          </button>
          <output>{t.size} px</output>
          <button type="button" className="secondary" aria-label="Larger text" disabled={t.size >= LIMITS.size.max} onClick={() => change({ size: stepSize(t.size, 1) })}>
            A+
          </button>
        </div>
      </div>
      <label className="tc-row">
        <span>Font</span>
        <select value={t.font} onChange={(e) => change({ font: e.target.value as FontKey })}>
          {Object.entries(FONTS).map(([key, f]) => (
            <option key={key} value={key}>
              {f.label}
            </option>
          ))}
        </select>
      </label>
      <label className="tc-row">
        <span>Weight</span>
        <select value={t.weight} onChange={(e) => change({ weight: Number(e.target.value) })}>
          {WEIGHTS.map((w) => (
            <option key={w.value} value={w.value}>
              {w.label}
            </option>
          ))}
        </select>
      </label>
      {slider('width', 'Line length', widthLabel(t.width))}
      {slider('line', 'Line spacing', `${t.line.toFixed(1)}×`)}
      {slider('letter', 'Letter spacing', spacingLabel(t.letter, LIMITS.letter))}
      {slider('word', 'Word spacing', spacingLabel(t.word, LIMITS.word))}
      <div className="tc-row">
        <span id="tc-align">Alignment</span>
        <div className="tc-align" role="radiogroup" aria-labelledby="tc-align">
          {ALIGNMENTS.map((a) => (
            <button
              key={a.value}
              type="button"
              role="radio"
              aria-checked={t.align === a.value}
              aria-label={a.label}
              title={a.label}
              className={t.align === a.value ? 'on' : 'secondary'}
              onClick={() => change({ align: a.value as Align })}
            >
              <svg width="16" height="14" viewBox="0 0 16 14" aria-hidden="true">
                {[0, 4, 8, 12].map((y, i) => {
                  const w = a.value === 'justify' || i % 2 === 0 ? 16 : 10
                  const x = a.value === 'center' ? (16 - w) / 2 : a.value === 'end' ? 16 - w : 0
                  return <rect key={y} x={x} y={y} width={w} height="2" rx="1" fill="currentColor" />
                })}
              </svg>
            </button>
          ))}
        </div>
      </div>
      <div>
        <button type="button" className="secondary" onClick={() => change('reset')}>
          Back to the standard text
        </button>
      </div>
    </div>
  )
}
