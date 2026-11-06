import { LearnedBar } from './LearnedBar'
import { useEffect, useState } from 'react'
import { getPref, getStats, setPref, type LanguageStats, type Stats as StatsData } from './api'
import { duration } from './bookStats'
import { growthPoints, relativeDay, visibleLanguages } from './readingStats'

const W = 640
const H = 150
const PAD = 8
const n = (x: number) => x.toLocaleString('en')

// A line from the first to the last point; the left caption is the first date, the right one the last.
function LineChart({ points, label, caption }: { points: { label: string; value: number }[]; label: string; caption: string }) {
  const max = Math.max(...points.map((p) => p.value), 1)
  const x = (i: number) => PAD + (i * (W - 2 * PAD)) / Math.max(points.length - 1, 1)
  const y = (v: number) => H - PAD - (v * (H - 2 * PAD)) / max
  return (
    <figure className="chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label}>
        <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} className="axis" />
        <polyline points={points.map((p, i) => `${x(i)},${y(p.value)}`).join(' ')} className="line" fill="none" />
      </svg>
      <figcaption className="muted">
        <span>{points[0].label}</span>
        <span>{caption}</span>
        <span>{points[points.length - 1].label}</span>
      </figcaption>
    </figure>
  )
}

function Kpi({ title, value, sub }: { title: string; value: string; sub?: string }) {
  return (
    <div className="kpi">
      <span className="kpi-title">{title}</span>
      <span className="kpi-big">
        {value}
      </span>
      {sub && <span className="muted kpi-sub">{sub}</span>}
    </div>
  )
}

function Section({ lang, detail, onOpen }: { lang: LanguageStats; detail: boolean; onOpen: () => void }) {
  const c = lang.coverage
  const counted = c.known + c.learning + c.new
  const part = (v: number) => (counted > 0 ? (100 * v) / counted : 0)
  const growth = growthPoints(lang.growth)
  return (
    <section className="lang-card" aria-labelledby={`lang-${lang.id}`}>
      <div className="lang-head">
        <h2 id={`lang-${lang.id}`}>{lang.name}</h2>
        {!detail && (
          <button className="secondary small" onClick={onOpen}>
            Details
          </button>
        )}
      </div>

      <LearnedBar learned={lang.learned} known={lang.terms.known} />

      <div className="kpis">
        <Kpi
          title="Your texts"
          value={c.knownPercent === null ? '—' : `${Math.round(c.knownPercent)}% known`}
          sub={lang.books.count === 0 ? 'No books' : `${lang.books.count} ${lang.books.count === 1 ? 'book' : 'books'} · ${n(c.words)} words`}
        />
        <Kpi title="Vocabulary" value={`${n(lang.terms.vocabulary)} words`} sub={`${n(lang.terms.known)} known · ${n(lang.terms.learning)} learning`} />
        <Kpi title="Read this week" value={`${n(lang.read.week)} words`} sub={`${n(lang.read.day)} today`} />
        <Kpi
          title="Streak"
          value={lang.streak > 0 ? `${lang.streak} ${lang.streak === 1 ? 'day' : 'days'}` : '—'}
          sub={lang.lastRead ? `last read ${relativeDay(lang.lastRead)}` : 'nothing read yet'}
        />
      </div>

      {counted > 0 && (
        <>
          <div className="statusbar" role="img" aria-label={`${Math.round(part(c.known))}% known, ${Math.round(part(c.learning))}% learning, ${Math.round(part(c.new))}% new`}>
            <i className="k" style={{ width: `${part(c.known)}%` }} />
            <i className="l" style={{ width: `${part(c.learning)}%` }} />
            <i className="n" style={{ width: `${part(c.new)}%` }} />
          </div>
          <p className="muted lang-line">
            {n(c.newUnique)} new words waiting in your texts{c.minutesLeft > 0 && <> · about {duration(c.minutesLeft)} of reading left</>}
            {c.pendingBooks > 0 && <> · counting the words of {c.pendingBooks} {c.pendingBooks === 1 ? 'book' : 'books'}…</>}
          </p>
        </>
      )}

      <dl className="read-row" aria-label="Words read">
        {(
          [
            ['Today', lang.read.day],
            ['7 days', lang.read.week],
            ['30 days', lang.read.month],
            ['Year', lang.read.year],
            ['All time', lang.read.total],
          ] as const
        ).map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{n(value)}</dd>
          </div>
        ))}
      </dl>

      {detail && (
        <>
          <div className="lang-more muted">
            {n(lang.terms.phrases)} phrases · {n(lang.terms.ignored)} ignored words · {n(lang.terms.unstarted)} seen but not started
            {lang.firstRead && <> · reading since {relativeDay(lang.firstRead)}</>}
          </div>
          {lang.chart.length > 1 && (
            <>
              <h3>Words read</h3>
              <LineChart
                points={lang.chart.map((p) => ({ label: p.readdate, value: p.runningTotal }))}
                label={`Words read in ${lang.name} over time`}
                caption={`${n(Math.max(...lang.chart.map((p) => p.runningTotal)))} words in all`}
              />
            </>
          )}
          {growth.length > 1 && (
            <>
              <h3>Known words</h3>
              <LineChart points={growth} label={`Known words in ${lang.name} over time`} caption={`${n(growth[growth.length - 1].value)} known now`} />
              <p className="muted lang-line">By the day each word reached Known.</p>
            </>
          )}
          <h3>Books</h3>
          {lang.books.list.length === 0 ? (
            <p className="muted">No books in {lang.name}.</p>
          ) : (
            <ul className="lang-books">
              {lang.books.list.map((b) => (
                <li key={b.id}>
                  <a href={`#/book/${b.id}/read/${b.currentPage}`}>{b.title}</a>
                  <span className="muted">
                    {b.pages > 1 ? `page ${b.currentPage} of ${b.pages}` : '1 page'} · {b.stats ? `${Math.round(b.stats.knownPercent)}% known` : 'counting…'}
                    {b.lastRead && <> · read {relativeDay(b.lastRead)}</>}
                  </span>
                  <progress value={b.currentPage - 1} max={Math.max(b.pages, 1)} aria-label={`Progress in ${b.title}`} />
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  )
}

export function Stats() {
  const [data, setData] = useState<StatsData | null>(null)
  const [error, setError] = useState('')
  const [choice, setChoice] = useState(() => getPref<string>('stats.language', 'all'))

  useEffect(() => {
    getStats().then(setData, (e) => setError(e.message))
  }, [])
  // Counting the words of a book takes a moment the first time: ask again after each answer until every book has its numbers.
  const pending = data?.languages.some((l) => l.coverage.pendingBooks > 0) ?? false
  useEffect(() => {
    if (!pending) return
    const timer = window.setTimeout(() => getStats().then(setData, () => undefined), 1800)
    return () => window.clearTimeout(timer)
  }, [data, pending])

  const pick = (value: string) => {
    setChoice(value)
    setPref('stats.language', value)
  }

  if (error) return <p className="error">{error}</p>
  if (!data) return <p className="muted">Loading…</p>
  const shown = visibleLanguages(data.languages, choice)
  const detail = shown.length === 1 && data.languages.length > 1 ? true : shown.length === 1 && choice !== 'all'
  return (
    <>
      <h1>Reading</h1>
      {data.languages.length === 0 ? (
        <p className="muted">Add a book to start. Words are counted when you finish a page in the reader.</p>
      ) : (
        <>
          {data.languages.length > 1 && (
            <div className="segmented" role="radiogroup" aria-label="Language">
              {[{ value: 'all', label: 'All languages' }, ...data.languages.map((l) => ({ value: String(l.id), label: l.name }))].map((o) => (
                <label key={o.value} className={choice === o.value || (o.value === 'all' && shown.length === data.languages.length) ? 'on' : ''}>
                  <input type="radio" name="language" value={o.value} checked={choice === o.value} onChange={() => pick(o.value)} />
                  {o.label}
                </label>
              ))}
            </div>
          )}

          <div className="summary-cards">
            <div className="summary-card">
              <span className="kpi-title">Streak</span>
              <strong>{data.streak > 0 ? `${data.streak} ${data.streak === 1 ? 'day' : 'days'}` : '—'}</strong>
              <span className="muted">{data.streak > 0 ? 'in a row' : 'finish a page to start one'}</span>
            </div>
            <div className="summary-card">
              <span className="kpi-title">Read today</span>
              <strong>{n(data.totals.readToday)}</strong>
              <span className="muted">words</span>
            </div>
            <div className="summary-card">
              <span className="kpi-title">This week</span>
              <strong>{n(data.totals.readWeek)}</strong>
              <span className="muted">words</span>
            </div>
            <div className="summary-card">
              <span className="kpi-title">Known words</span>
              <strong>{n(data.totals.known)}</strong>
              <span className="muted">+ {n(data.totals.learning)} learning</span>
            </div>
            <div className="summary-card">
              <span className="kpi-title">Books</span>
              <strong>{n(data.totals.books)}</strong>
              <span className="muted">{data.languages.length} {data.languages.length === 1 ? 'language' : 'languages'}</span>
            </div>
          </div>

          {shown.map((lang) => (
            <Section key={lang.id} lang={lang} detail={detail} onOpen={() => pick(String(lang.id))} />
          ))}
        </>
      )}
    </>
  )
}
