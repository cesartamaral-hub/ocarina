const KEYS: [string, string][] = [
  ['click a word', 'open it in the side panel'],
  ['drag over words', 'make a phrase'],
  ['⌘ or Ctrl + click', 'pick several words for one status change'],
  ['1 2 3 4 5', 'set the status of the open word (or the picked words)'],
  ['w', 'well known'],
  ['i', 'ignore'],
  ['← →', 'previous or next page'],
  ['Esc', 'clear the selection'],
  ['?', 'show or hide this list'],
]

export function KeyHelp({ onClose }: { onClose: () => void }) {
  return (
    <section className="panel static key-help" aria-label="Keyboard shortcuts">
      <table>
        <tbody>
          {KEYS.map(([key, what]) => (
            <tr key={key}>
              <th>
                <kbd>{key}</kbd>
              </th>
              <td>{what}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <button className="secondary" onClick={onClose}>
        Close
      </button>
    </section>
  )
}
