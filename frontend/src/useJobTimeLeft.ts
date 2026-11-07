import { useEffect, useState } from 'react'
import { isActive, type Job } from './api'
import { timeLeft } from './estimate'

// The time left of a running job, from how fast it has gone since it was first seen running. '' while there is nothing to go on.
export function useJobTimeLeft(job: Job | null): string {
  const id = isActive(job) && job!.state === 'running' ? job!.id : null
  const [clock, setClock] = useState<{ id: string; from: number; now: number } | null>(null)
  useEffect(() => {
    if (!id) return
    const from = Date.now()
    const tick = () => setClock({ id, from, now: Date.now() })
    const timer = setInterval(tick, 2000)
    return () => clearInterval(timer)
  }, [id])
  if (!job || !clock || clock.id !== job.id) return ''
  return timeLeft((clock.now - clock.from) / 1000, job.done, job.total)
}
