import { useState } from 'react'
import { appearance, saveAppearance, SIZE_RANGE, type ReaderFont, type Theme } from './appearanceSettings'

export function Appearance() {
  const [settings, setSettings] = useState(appearance)
  const change = (patch: Partial<typeof settings>) => {
    saveAppearance(patch)
    setSettings({ ...settings, ...patch })
  }
  return (
    <>
      <p>
        <a href="#/settings">← Settings</a>
      </p>
      <h1>Appearance</h1>
      <div className="form appearance">
        <label>
          Theme
          <select value={settings.theme} onChange={(e) => change({ theme: e.target.value as Theme })}>
            <option value="system">Follow the system</option>
            <option value="light">Light</option>
            <option value="dark">Dark</option>
          </select>
        </label>
        <label>
          Text size in the reader: {settings.size} px
          <input
            type="range"
            min={SIZE_RANGE.min}
            max={SIZE_RANGE.max}
            value={settings.size}
            onChange={(e) => change({ size: Number(e.target.value) })}
          />
        </label>
        <label>
          Font in the reader
          <select value={settings.font} onChange={(e) => change({ font: e.target.value as ReaderFont })}>
            <option value="sans">Sans serif</option>
            <option value="serif">Serif</option>
          </select>
        </label>
        <div>
          <button className="secondary" onClick={() => change({ size: SIZE_RANGE.standard, font: 'sans', theme: 'system' })}>
            Back to the standard look
          </button>
        </div>
        <p className="muted">How the text will look:</p>
        <article className="appearance-sample">
          <p>
            Elke ochtend sta ik vroeg op, ik drink koffie en ik fiets naar mijn werk. Każdego ranka wstaję wcześnie. Chaque matin, je me lève tôt.
          </p>
        </article>
      </div>
    </>
  )
}
