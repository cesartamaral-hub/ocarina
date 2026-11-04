import { AlignPicker } from './AlignPicker'
import { useTypography } from './useTypography'
import {
  FONTS,
  LIMITS,
  WEIGHTS,
  spacingLabel,
  stepSize,
  widthLabel,
  type FontKey,
} from './typography'

type Numeric = 'width' | 'line' | 'letter' | 'word'

// The text controls, shared by the "Aa" popover in the reader and the Appearance page. Changes apply at once.
export function TypographyControls() {
  const [t, change] = useTypography()
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
        <AlignPicker value={t.align} onChange={(align) => change({ align })} />
      </div>
      <div>
        <button type="button" className="secondary" onClick={() => change('reset')}>
          Back to the standard text
        </button>
      </div>
    </div>
  )
}
