import { useEffect, useState } from 'react'
import { getStats, type ChartPoint, type Stats as StatsData } from './api'

const W = 640
const H = 160
const PAD = 8

// Running total of words read, as a line from the first to the last day.
function Chart({ points }: { points: ChartPoint[] }) {
  const max = Math.max(...points.map((p) => p.runningTotal), 1)
  const x = (i: number) => PAD + (i * (W - 2 * PAD)) / Math.max(points.length - 1, 1)
  const y = (v: number) => H - PAD - (v * (H - 2 * PAD)) / max
  const line = points.map((p, i) => `${x(i)},${y(p.runningTotal)}`).join(' ')
  return (
    <figure className="chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Words read over time">
        <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} className="axis" />
        <polyline points={line} className="line" fill="none" />
      </svg>
      <figcaption className="muted">
        <span>{points[0].readdate}</span>
        <span>{max.toLocaleString()} words in all</span>
        <span>{points[points.length - 1].readdate}</span>
      </figcaption>
    </figure>
  )
}

export function Stats() {
  const [data, setData] = useState<StatsData | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    getStats().then(setData, (e) => setError(e.message))
  }, [])
  if (error) return <p className="error">{error}</p>
  if (!data) return <p className="muted">Loading…</p>
  return (
    <>
      <h1>Reading</h1>
      <p>
        {data.streak > 0 ? (
          <strong>
            {data.streak} {data.streak === 1 ? 'day' : 'days'} in a row
          </strong>
        ) : (
          <span className="muted">No reading streak right now. Finish a page to start one.</span>
        )}
      </p>
      {data.table.length === 0 ? (
        <p className="muted">Words are counted when you finish a page in the reader.</p>
      ) : (
        <>
          <h2>Words read</h2>
          <table className="terms">
            <thead>
              <tr>
                <th>Language</th>
                <th>Today</th>
                <th>7 days</th>
                <th>30 days</th>
                <th>Year</th>
                <th>All time</th>
              </tr>
            </thead>
            <tbody>
              {data.table.map((r) => (
                <tr key={r.name}>
                  <td>{r.name}</td>
                  {[r.counts.day, r.counts.week, r.counts.month, r.counts.year, r.counts.total].map((n, i) => (
                    <td key={i}>{n.toLocaleString()}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {Object.entries(data.chart).map(([name, points]) => (
            <section key={name}>
              <h2>{name}</h2>
              <Chart points={points} />
            </section>
          ))}
        </>
      )}
    </>
  )
}
