import { useState } from 'react'
import { appearance, saveAppearance, type Theme } from './appearanceSettings'
import { TypographyControls } from './TypographyControls'

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
        <h2>Text in the reader</h2>
        <TypographyControls />
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
