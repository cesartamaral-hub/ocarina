import { useEffect } from 'react'

// Unsaved work that clicking a link would lose (the text editor). Things register while they hold changes; the
// click handler in App.tsx asks before following a link to another page, and does nothing for anything else.
const guards: string[] = []

export function useLeaveGuard(active: boolean, message: string): void {
  useEffect(() => {
    if (!active) return
    guards.push(message)
    return () => {
      const at = guards.lastIndexOf(message)
      if (at >= 0) guards.splice(at, 1)
    }
  }, [active, message])
}

// What to ask before following `href` from the page at `current`, or null to just go ahead.
export function questionBeforeLeaving(href: string | null, current: string, pending: readonly string[] = guards): string | null {
  if (pending.length === 0 || !href || !href.startsWith('#/')) return null // not a page link
  if (href === current) return null // already there
  return pending[pending.length - 1]
}

// For the capture-phase click handler: true when the click may go ahead.
export function mayFollow(link: { getAttribute: (name: string) => string | null } | null, ask: (question: string) => boolean): boolean {
  const question = questionBeforeLeaving(link?.getAttribute('href') ?? null, window.location.hash)
  return question === null || ask(question)
}
