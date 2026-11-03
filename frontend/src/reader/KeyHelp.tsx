import { ACTIONS, keyLabel, keyOf } from '../shortcutKeys'

const MOUSE: [string, string][] = [
  ['click a word', 'open it in the side panel'],
  ['drag over words', 'make a phrase'],
  ['⌘ or Ctrl + click', 'pick several words for one status change'],
]

export function KeyHelp({ onClose }: { onClose: () => void }) {
  return (
    <section className="panel static key-help" aria-label="Keyboard shortcuts">
      <table>
        <tbody>
          {MOUSE.map(([how, what]) => (
            <tr key={how}>
              <th>
                <kbd>{how}</kbd>
              </th>
              <td>{what}</td>
            </tr>
          ))}
          {ACTIONS.map((a) => (
            <tr key={a.id}>
              <th>
                <kbd>{keyLabel(keyOf(a.id))}</kbd>
              </th>
              <td>{a.label}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="muted">
        <a href="#/shortcuts">Change the keys</a>
      </p>
      <button className="secondary" onClick={onClose}>
        Close
      </button>
    </section>
  )
}
