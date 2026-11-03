import { useEffect, useState } from 'react'
import { ACTIONS, assignKey, keyLabel, keyOf, resetKeys } from './shortcutKeys'

export function Shortcuts() {
  const [listening, setListening] = useState<string | null>(null)
  const [, setVersion] = useState(0)
  const [error, setError] = useState('')

  // While an action is waiting for its new key, the next key press is that key.
  useEffect(() => {
    if (!listening) return
    function onKey(e: KeyboardEvent) {
      e.preventDefault()
      e.stopPropagation()
      if (e.key === 'Escape' && listening !== 'clear') {
        setListening(null)
        return
      }
      const problem = assignKey(listening!, e.key)
      setError(problem ?? '')
      if (!problem) {
        setListening(null)
        setVersion((v) => v + 1)
      }
    }
    window.addEventListener('keydown', onKey, true)
    return () => window.removeEventListener('keydown', onKey, true)
  }, [listening])

  return (
    <>
      <p>
        <a href="#/settings">← Settings</a>
      </p>
      <h1>Keyboard shortcuts</h1>
      <p className="muted">Click a key, then press the one you want instead. Esc cancels. These work in the reader.</p>
      <table className="dicts shortcuts">
        <tbody>
          {ACTIONS.map((a) => (
            <tr key={a.id}>
              <td>{a.label}</td>
              <td>
                <button className="secondary key" onClick={() => (setError(''), setListening(listening === a.id ? null : a.id))}>
                  {listening === a.id ? 'Press a key…' : <kbd>{keyLabel(keyOf(a.id))}</kbd>}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {error && <p className="error">{error}</p>}
      <p>
        <button
          className="secondary"
          onClick={() => {
            resetKeys()
            setListening(null)
            setError('')
            setVersion((v) => v + 1)
          }}
        >
          Back to the standard keys
        </button>
      </p>
    </>
  )
}
