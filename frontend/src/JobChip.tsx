import { useEffect, useState } from 'react'
import { getActiveJobs, getJob, type Job } from './api'
import { percent } from './format'
import { notify } from './notices'

const describe = (j: Job): { text: string; href: string } => {
  if (j.kind === 'download') {
    return { text: `Downloading ${j.title ?? 'a model'}${j.state === 'running' && j.total ? ` · ${percent(j.done, j.total)}%` : ''}`, href: '#/settings/models' }
  }
  if (j.kind === 'sync') {
    return { text: `Syncing “${j.title ?? 'a book'}”${j.state === 'running' && j.total ? ` · ${j.done}/${j.total}` : ''}`, href: j.book_id ? `#/book/${j.book_id}/audio` : '#/' }
  }
  if (j.kind === 'translate') {
    return { text: `Translating “${j.title ?? 'a book'}”${j.state === 'running' && j.total ? ` · ${j.done}/${j.total}` : ''}`, href: j.book_id ? `#/book/${j.book_id}` : '#/' }
  }
  if (j.kind === 'preview') return { text: 'Making a voice preview', href: '#/settings/models' }
  if (j.kind === 'check' || j.phase === 'testing') return { text: `Testing ${j.title ?? 'a model'}`, href: '#/settings/models' }
  return {
    text: `Voicing “${j.title ?? 'a book'}”${j.state === 'running' && j.total ? ` · ${j.done}/${j.total}` : ''}`,
    href: j.book_id ? `#/book/${j.book_id}/audio` : '#/',
  }
}

const finishedMessage = (j: Job): string | null => {
  if (j.state === 'done' && j.kind === 'check') return `${j.title ?? 'The model'} was tested: see Settings for the result`
  if (j.state === 'done' && j.kind === 'translate') return `The translation of “${j.title}” is ready`
  if (j.state === 'done' && j.kind === 'sync') {
    const doubtful = j.suspect ? `, but ${j.suspect} ${j.suspect === 1 ? 'sentence' : 'sentences'} could not be placed with confidence` : ''
    return `“${j.title}” is synced with the text${doubtful}`
  }
  if (j.state === 'done') return j.kind === 'download' ? `${j.title ?? 'The model'} is ready to use` : j.kind === 'audio' ? `Audio for “${j.title}” is ready` : null
  if (j.state === 'error') return `${j.title ?? 'A job'} failed: ${j.error ?? 'unknown error'}`
  return null
}

// Shows what is running in the background wherever you are in the app, and says when it finishes.
export function JobChip() {
  const [jobs, setJobs] = useState<Job[]>([])
  useEffect(() => {
    const watch = { known: new Map<string, Job>(), stopped: false }
    async function poll() {
      try {
        const active = await getActiveJobs()
        if (watch.stopped) return
        const now = new Map(active.map((j) => [j.id, j]))
        for (const [id, before] of watch.known) {
          if (now.has(id)) continue
          const final = await getJob(id).catch(() => null)
          const message = final && finishedMessage({ ...before, ...final })
          if (message) notify(message, final?.state === 'error' ? 8000 : 4000)
        }
        watch.known = now
        setJobs(active)
      } catch {
        // The server may be busy; the next poll will do.
      }
    }
    poll()
    const timer = setInterval(poll, 1500)
    return () => {
      watch.stopped = true
      clearInterval(timer)
    }
  }, [])
  if (jobs.length === 0) return null
  const first = describe(jobs[0])
  const more = jobs.length - 1
  return (
    <a className="job-chip" href={first.href} title="Background work">
      <span className="spinner" aria-hidden="true" />
      <span>{first.text}</span>
      {more > 0 && <span className="muted">+{more} waiting</span>}
    </a>
  )
}
