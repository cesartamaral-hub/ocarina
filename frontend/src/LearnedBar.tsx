import { progress } from './learnedGoal'

const n = (v: number) => v.toLocaleString()

// How many words you learned in Ocarina and how far that is to the next step (or the goal you set). A word counts when you took it to Known
// yourself; words marked known when finishing a page, and words you knew before, do not (unless you chose to count those).
export function LearnedBar({ learned, goal, known = 0, countsPrior = false }: { learned: number; goal?: number | null; known?: number; countsPrior?: boolean }) {
  const p = progress(learned, goal)
  const before = !countsPrior && known > learned ? known - learned : 0
  const what = `Words you took to Known yourself. Words marked known when finishing a page${countsPrior ? '' : ', and words you knew before'} do not count.`
  return (
    <div className="learned" title={what}>
      <div className="learned-line">
        <span className="learned-count">{n(learned)}</span>
        <span> learned in Ocarina</span>
        <span className="muted learned-next">{goal && goal > learned ? 'Goal' : 'Next step'}: {n(p.goal)}</span>
      </div>
      <div className="learned-bar" role="progressbar" aria-valuemin={0} aria-valuemax={p.goal} aria-valuenow={learned} aria-label={`${n(learned)} words learned, ${n(p.toGo)} to ${n(p.goal)}`}>
        <i style={{ width: `${p.fraction * 100}%` }} />
      </div>
      {before > 0 && <div className="muted learned-before">{n(before)} more known from before</div>}
    </div>
  )
}
