import { useCallback, useEffect, useRef, useState } from 'react'
import {
  cancelJob,
  getActiveJobs,
  getBookTranslation,
  getJob,
  isActive,
  removeBookTranslation,
  startBookTranslation,
  type BookTranslation,
  type Job,
} from '../api'

// The book's translation and the job making it. While a job runs the sentences that are done appear in the text as they finish.
export function useBookTranslation(bookId: number, onDone?: (data: BookTranslation) => void) {
  const [data, setData] = useState<BookTranslation | null>(null)
  const [job, setJob] = useState<Job | null>(null)
  const [error, setError] = useState('')

  const finished = useRef(onDone)
  useEffect(() => {
    finished.current = onDone
  })
  const refresh = useCallback(
    () =>
      getBookTranslation(bookId).then(
        (d) => (setData(d), d),
        () => null,
      ),
    [bookId],
  )
  useEffect(() => {
    refresh()
    getActiveJobs().then(
      (jobs) => setJob((cur) => cur ?? jobs.find((j) => j.kind === 'translate' && j.book_id === bookId) ?? null),
      () => undefined,
    )
  }, [bookId, refresh])

  const jobId = isActive(job) ? job!.id : null
  useEffect(() => {
    if (!jobId) return
    const timer = setInterval(async () => {
      const j = await getJob(jobId).catch(() => null)
      if (!j) return
      setJob(j)
      const fresh = await refresh()
      if (j.state === 'done' && fresh) finished.current?.(fresh) // the translation is ready: the reader may switch its view
    }, 1500)
    return () => clearInterval(timer)
  }, [jobId, refresh])

  const start = useCallback(
    async (
      scope: 'page' | 'book',
      page?: number,
      method?: { provider: string; model: string | null },
      redo = false,
    ) => {
      setError('')
      try {
        setJob(await startBookTranslation(bookId, scope, page, method, redo))
      } catch (e) {
        setError((e as Error).message)
      }
    },
    [bookId],
  )
  const cancel = useCallback(async () => {
    if (job) setJob(await cancelJob(job.id).catch(() => job))
  }, [job])
  const remove = useCallback(async () => {
    setError('')
    try {
      await removeBookTranslation(bookId)
      setJob(null)
      refresh()
    } catch (e) {
      setError((e as Error).message)
    }
  }, [bookId, refresh])

  return { data, refresh, job, running: isActive(job), error, start, cancel, remove }
}
