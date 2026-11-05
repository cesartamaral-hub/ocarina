import { LEVELS, progressFor } from './cefr'

const n = (v: number) => v.toLocaleString()

// How far a vocabulary has come on the CEFR scale: a bar of six stretches (A1 to C2), the level reached, and the way to the next one.
// With `detail` it is bigger and lists each level, what it means and how many words it needs.
export function CefrBar({ known, learning = 0, detail = false }: { known: number; learning?: number; detail?: boolean }) {
  const p = progressFor(known)
  const summary = p.next
    ? `${n(known)} known words · ${p.label} · ${Math.round(p.fraction * 100)}% of the way to ${p.next.id}`
    : `${n(known)} known words · ${p.label}, the top level`
  return (
    <div className={`cefr${detail ? ' detail' : ''}`}>
      <div className="cefr-line">
        <strong className="cefr-level" title={p.level ? `${p.level.name}: ${p.level.blurb}` : 'Fewer than 500 known words: before A1'}>
          {p.label}
        </strong>
        <span className="cefr-words">{n(known)} words</span>
        {p.next ? (
          <span className="muted cefr-next">
            {Math.round(p.fraction * 100)}% to {p.next.id} · {n(p.toNext)} to go
          </span>
        ) : (
          <span className="muted cefr-next">the top level</span>
        )}
      </div>
      <div className="cefr-bar" role="img" aria-label={summary}>
        {LEVELS.map((l, i) => (
          <span key={l.id} className={`cefr-seg${p.segments[i] >= 1 ? ' done' : ''}${p.next?.id === l.id ? ' now' : ''}`} title={`${l.id} ${l.name}: ${n(l.words)} words`}>
            <i style={{ width: `${p.segments[i] * 100}%` }} />
            <b>{l.id}</b>
          </span>
        ))}
      </div>
      {detail && (
        <>
          <table className="cefr-table">
            <thead>
              <tr>
                <th>Level</th>
                <th>What it looks like</th>
                <th>Words</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {LEVELS.map((l) => {
                const reached = known >= l.words
                const now = p.next?.id === l.id
                return (
                  <tr key={l.id} className={reached ? 'reached' : now ? 'now' : ''}>
                    <th scope="row">
                      {l.id} <span className="muted">{l.name}</span>
                    </th>
                    <td>{l.blurb}</td>
                    <td className="cefr-count" title={`Estimates range from ${l.range}`}>
                      {n(l.words)}
                    </td>
                    <td className="cefr-state">{reached ? '✓ reached' : now ? `${n(l.words - known)} to go` : ''}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          <p className="muted cefr-note">
            Counted from the words you know (statuses 4, 5 and well known).{' '}
            {learning > 0 && p.next && known + learning >= p.next.words ? `Learning your ${n(learning)} words in progress would take you to ${progressFor(known + learning).label}. ` : learning > 0 ? `${n(learning)} more are in progress. ` : ''}
            These are rough guides: estimates differ by study and by whether vocabulary is active or passive, and every form of a word counts separately here. Ranges found in studies: {LEVELS.map((l) => `${l.id} ${l.range}`).join(' · ')}.
          </p>
        </>
      )}
    </div>
  )
}
